"""Tests for EQS auth manager and HTTP client."""

import time
from unittest.mock import MagicMock, patch, call

import pytest

from clients.eqs_client import EQSAuthManager, EQSClient, AuthError


FAKE_TOKEN = "fake-access-token-abc123"
FAKE_REFRESH = "fake-refresh-token-xyz789"
NEW_TOKEN = "new-access-token-after-refresh"

OAUTH_ENDPOINT = "https://api.integrityline.com/oauth/token"


def _make_manager() -> EQSAuthManager:
    return EQSAuthManager(
        client_id="test-client-id",
        client_secret="test-client-secret",
        oauth_endpoint=OAUTH_ENDPOINT,
    )


def _mock_login_response(token=FAKE_TOKEN, refresh=FAKE_REFRESH):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token, "refresh_token": refresh}
    return resp


def _mock_http_client(login_resp=None):
    http = MagicMock()
    http.post.return_value = login_resp or _mock_login_response()
    return http


class TestEQSAuthManager:
    def test_get_token_returns_access_token(self):
        manager = _make_manager()
        http = _mock_http_client()

        token = manager.get_token(http)

        assert token == FAKE_TOKEN
        http.post.assert_called_once()

    def test_get_token_caches_within_ttl(self):
        manager = _make_manager()
        http = _mock_http_client()

        token1 = manager.get_token(http)
        token2 = manager.get_token(http)

        assert token1 == token2
        # Should only have called the auth endpoint once
        assert http.post.call_count == 1

    def test_get_token_refreshes_when_expired(self):
        manager = _make_manager()
        http = _mock_http_client()

        # Get initial token
        manager.get_token(http)

        # Simulate access token expiry
        manager._token_obtained_at = time.time() - (manager.ACCESS_TOKEN_TTL + 1)

        # Set up refresh response
        refresh_resp = MagicMock()
        refresh_resp.status_code = 200
        refresh_resp.json.return_value = {
            "access_token": NEW_TOKEN,
            "refresh_token": FAKE_REFRESH,
        }
        http.post.return_value = refresh_resp

        new_token = manager.get_token(http)

        assert new_token == NEW_TOKEN
        assert http.post.call_count == 2

    def test_get_token_reauths_when_refresh_fails(self):
        manager = _make_manager()
        http = _mock_http_client()

        manager.get_token(http)
        manager._token_obtained_at = time.time() - (manager.ACCESS_TOKEN_TTL + 1)

        # Refresh fails
        fail_resp = MagicMock()
        fail_resp.status_code = 401
        fail_resp.json.return_value = {"error": "invalid_grant"}

        # Re-login succeeds with new token
        relogin_resp = MagicMock()
        relogin_resp.status_code = 200
        relogin_resp.json.return_value = {
            "access_token": NEW_TOKEN,
            "refresh_token": "brand-new-refresh",
        }

        http.post.side_effect = [fail_resp, relogin_resp]

        new_token = manager.get_token(http)
        assert new_token == NEW_TOKEN

    def test_invalidate_forces_reauth(self):
        manager = _make_manager()
        http = _mock_http_client()

        manager.get_token(http)
        manager.invalidate()

        # Next call should re-authenticate (session expired after invalidate sets _token_obtained_at=0)
        # but session is still valid unless we also expire session
        manager._session_started_at = 0.0  # force full re-auth
        manager.get_token(http)

        assert http.post.call_count == 2

    def test_login_failure_raises_auth_error(self):
        manager = _make_manager()
        http = MagicMock()
        fail_resp = MagicMock()
        fail_resp.status_code = 401
        fail_resp.text = "Unauthorized"
        http.post.return_value = fail_resp

        with pytest.raises(AuthError, match="Login failed"):
            manager.get_token(http)

    def test_handles_eqs_custom_token_field(self):
        """EQS may return 'token' instead of standard 'access_token'."""
        manager = _make_manager()
        http = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"token": "custom-token", "refresh_token": "r"}
        http.post.return_value = resp

        token = manager.get_token(http)
        assert token == "custom-token"


class TestEQSClientRetryOn401:
    def test_retries_on_401_with_fresh_token(self):
        """Client should invalidate token and retry once on 401."""
        with patch("clients.eqs_client.get_auth_manager") as mock_get_auth:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = FAKE_TOKEN
            mock_get_auth.return_value = mock_auth

            client = EQSClient(base_url="https://fake-api.example.com")

            # First GET returns 401, second returns 200
            first_resp = MagicMock()
            first_resp.status_code = 401

            second_resp = MagicMock()
            second_resp.status_code = 200
            second_resp.json.return_value = {"results": [], "totalPages": 0}
            second_resp.raise_for_status = MagicMock()

            client._http.get = MagicMock(side_effect=[first_resp, second_resp])

            result = client.list_cases()

            assert result == {"results": [], "totalPages": 0}
            # invalidate should have been called after the 401
            mock_auth.invalidate.assert_called_once()
            assert client._http.get.call_count == 2
