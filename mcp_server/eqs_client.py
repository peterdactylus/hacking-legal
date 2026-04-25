"""EQS Integrity Line API client with OAuth2 auth management."""

import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

EQS_API_BASE = os.getenv("EQS_API_BASE", "https://api-compliance.eqscockpit.com/integrations")
EQS_OAUTH_ENDPOINT = os.getenv("EQS_OAUTH_ENDPOINT", "https://api.integrityline.com/oauth/token")


class AuthError(Exception):
    pass


class EQSAuthManager:
    """Manages OAuth2 client_credentials token lifecycle for the EQS API."""

    ACCESS_TOKEN_TTL = 14 * 60   # 14 min (15 min actual, refresh 1 min early)
    SESSION_TTL = 23 * 60 * 60   # 23 hr (24 hr actual)

    def __init__(self, client_id: str, client_secret: str, oauth_endpoint: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oauth_endpoint = oauth_endpoint

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_obtained_at: float = 0.0
        self._session_started_at: float = 0.0

    def _token_expired(self) -> bool:
        return time.time() - self._token_obtained_at >= self.ACCESS_TOKEN_TTL

    def _session_expired(self) -> bool:
        return time.time() - self._session_started_at >= self.SESSION_TTL

    def _do_login(self, client: httpx.Client) -> None:
        resp = client.post(
            self.oauth_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if resp.status_code != 200:
            raise AuthError(f"Login failed: {resp.status_code} {resp.text}")

        body = resp.json()
        # Handle both standard OAuth2 response and EQS custom response formats
        self._access_token = body.get("access_token") or body.get("token")
        self._refresh_token = body.get("refresh_token")
        now = time.time()
        self._token_obtained_at = now
        if self._session_started_at == 0.0:
            self._session_started_at = now

    def _do_refresh(self, client: httpx.Client) -> bool:
        """Attempt token refresh. Returns False if refresh fails (session expired)."""
        if not self._refresh_token:
            return False
        resp = client.post(
            self.oauth_endpoint,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )
        if resp.status_code != 200:
            return False

        body = resp.json()
        self._access_token = body.get("access_token") or body.get("token")
        self._refresh_token = body.get("refresh_token", self._refresh_token)
        self._token_obtained_at = time.time()
        return True

    def get_token(self, client: httpx.Client) -> str:
        """Return a valid access token, refreshing or re-authenticating as needed."""
        if self._session_expired() or self._access_token is None:
            self._session_started_at = 0.0
            self._do_login(client)
        elif self._token_expired():
            if not self._do_refresh(client):
                self._session_started_at = 0.0
                self._do_login(client)
        return self._access_token

    def invalidate(self) -> None:
        """Force re-auth on next get_token call (call this on a 401 response)."""
        self._token_obtained_at = 0.0


def _make_auth_manager() -> EQSAuthManager:
    client_id = os.getenv("EQS_CLIENT_ID", "")
    client_secret = os.getenv("EQS_CLIENT_SECRET", "")
    oauth_endpoint = os.getenv("EQS_OAUTH_ENDPOINT", EQS_OAUTH_ENDPOINT)
    if not client_id or not client_secret:
        raise AuthError("EQS_CLIENT_ID and EQS_CLIENT_SECRET must be set")
    return EQSAuthManager(client_id, client_secret, oauth_endpoint)


_auth_manager: EQSAuthManager | None = None


def get_auth_manager() -> EQSAuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = _make_auth_manager()
    return _auth_manager


class EQSClient:
    """Thin HTTP client for the EQS Integrity Line Case API."""

    def __init__(self, base_url: str = EQS_API_BASE):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=30)
        self._auth = get_auth_manager()

    def _headers(self) -> dict:
        token = self._auth.get_token(self._http)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Language": "en",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._http.get(url, headers=self._headers(), params=params)
        if resp.status_code == 401:
            # Token may have just expired — invalidate and retry once
            self._auth.invalidate()
            resp = self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def list_cases(
        self,
        page_size: int = 20,
        current_page: int = 0,
        from_date: str | None = None,
        to_date: str | None = None,
        has_external_id: bool | None = None,
        external_case_id: str | None = None,
    ) -> dict:
        params: dict = {"pageSize": page_size, "currentPage": current_page}
        if from_date:
            params["fromCreatedDate"] = from_date
        if to_date:
            params["toCreatedDate"] = to_date
        if has_external_id is not None:
            params["hasExternalCaseId"] = str(has_external_id).lower()
        if external_case_id:
            params["externalCaseId"] = external_case_id
        return self._get("/api/v1/integrityline/cases", params)

    def get_case(self, case_id: int, language_iso: str = "en") -> dict:
        return self._get(
            f"/api/v1/integrityline/cases/{case_id}",
            params={"languageIso": language_iso},
        )

    def close(self) -> None:
        self._http.close()
