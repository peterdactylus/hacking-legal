"""Legal Data Analytics (Otto Schmidt) API client."""

import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

LDA_API_BASE = os.getenv("LDA_API_BASE", "https://otto-schmidt.legal-data-hub.com")
LDA_TOKEN_ENDPOINT = os.getenv("LDA_TOKEN_ENDPOINT", "https://online.otto-schmidt.de/token")


class LDAAuthError(Exception):
    pass


class LDAClient:
    """HTTP client for the Legal Data Analytics API."""

    TOKEN_TTL = 50 * 60  # 50 min conservative (actual TTL unspecified)

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str = LDA_API_BASE,
        token_endpoint: str = LDA_TOKEN_ENDPOINT,
    ):
        self.client_id = client_id or os.getenv("LDA_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("LDA_CLIENT_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self.token_endpoint = token_endpoint

        if not self.client_id or not self.client_secret:
            raise LDAAuthError("LDA_CLIENT_ID and LDA_CLIENT_SECRET must be set")

        self._http = httpx.Client(timeout=60)
        self._token: str | None = None
        self._token_obtained_at: float = 0.0

    def _token_expired(self) -> bool:
        return time.time() - self._token_obtained_at >= self.TOKEN_TTL

    def _authenticate(self) -> None:
        resp = self._http.post(
            self.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if resp.status_code != 200:
            raise LDAAuthError(f"Authentication failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["access_token"]
        self._token_obtained_at = time.time()

    def _get_token(self) -> str:
        if self._token is None or self._token_expired():
            self._authenticate()
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._http.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            # Token may have expired — re-auth and retry once
            self._token = None
            resp = self._http.request(method, url, headers=self._headers(), **kwargs)
        resp.raise_for_status()
        return resp.json()

    def list_data_assets(self) -> dict:
        """Return all available legal data assets (indices)."""
        return self._request("GET", "/api/data-assets")

    def semantic_search(
        self,
        query: str,
        data_asset: str,
        candidates: int = 10,
        post_reranking: bool = True,
        filters: list | None = None,
    ) -> dict:
        """Search for semantically relevant document sections."""
        body: dict = {
            "search_query": query,
            "data_asset": data_asset,
            "candidates": min(candidates, 20),
            "post_reranking": post_reranking,
        }
        if filters:
            body["filter"] = filters
        return self._request("POST", "/api/semantic-search", json=body)

    def qna(
        self,
        question: str,
        data_asset: str,
        mode: str = "attribution",
        filters: list | None = None,
    ) -> dict:
        """Ask a natural language question against a legal data asset."""
        body: dict = {
            "data_asset": data_asset,
            "prompt": question,
            "mode": mode,
            "filter": filters or [],
        }
        return self._request("POST", "/api/qna", json=body)

    def chat(self, messages: list[dict], data_asset: str) -> dict:
        """Send a multi-turn conversation against a legal data asset.

        Each message must have 'role' ('user' or 'assistant') and 'text'.
        """
        return self._request("POST", "/api/chat", json={
            "messages": messages,
            "data_asset": data_asset,
        })

    def clause_check(self, clause: str, data_asset: str) -> dict:
        """Analyze a contract clause for legal validity and appropriateness."""
        return self._request("POST", "/api/analyzer/clause-check", json={
            "data_asset": data_asset,
            "prompt": clause,
            "mode": "check",
            "filter": [],
        })

    def close(self) -> None:
        self._http.close()
