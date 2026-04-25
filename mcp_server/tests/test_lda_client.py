"""Tests for the Legal Data Analytics (Otto Schmidt) client."""

import time
from unittest.mock import MagicMock, patch

import pytest

from clients.lda_client import LDAClient, LDAAuthError


FAKE_TOKEN = "fake-lda-token-abc123"
NEW_TOKEN = "new-lda-token-after-reauth"


def _make_client() -> LDAClient:
    return LDAClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        base_url="https://fake-lda.example.com",
        token_endpoint="https://fake-token.example.com/token",
    )


def _token_response(token=FAKE_TOKEN):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": token}
    return resp


def _ok_response(body: dict):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status: int):
    resp = MagicMock()
    resp.status_code = status
    resp.text = "error"
    resp.raise_for_status = MagicMock(side_effect=Exception(f"HTTP {status}"))
    return resp


class TestLDAClientAuth:
    def test_authenticates_on_first_request(self):
        client = _make_client()
        client._http.post = MagicMock(return_value=_token_response())
        client._http.request = MagicMock(return_value=_ok_response({"data_assets": []}))

        client.list_data_assets()

        client._http.post.assert_called_once()
        call_kwargs = client._http.post.call_args
        assert "grant_type" in call_kwargs.kwargs.get("data", {}) or \
               "grant_type" in (call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})

    def test_caches_token_within_ttl(self):
        client = _make_client()
        client._http.post = MagicMock(return_value=_token_response())
        client._http.request = MagicMock(return_value=_ok_response({"data_assets": []}))

        client.list_data_assets()
        client.list_data_assets()

        assert client._http.post.call_count == 1

    def test_reauthenticates_when_token_expired(self):
        client = _make_client()
        client._http.post = MagicMock(side_effect=[
            _token_response(FAKE_TOKEN),
            _token_response(NEW_TOKEN),
        ])
        client._http.request = MagicMock(return_value=_ok_response({"data_assets": []}))

        client.list_data_assets()
        # Force expiry
        client._token_obtained_at = time.time() - (client.TOKEN_TTL + 1)
        client.list_data_assets()

        assert client._http.post.call_count == 2
        assert client._token == NEW_TOKEN

    def test_raises_on_auth_failure(self):
        client = _make_client()
        fail_resp = MagicMock()
        fail_resp.status_code = 401
        fail_resp.text = "Unauthorized"
        client._http.post = MagicMock(return_value=fail_resp)

        with pytest.raises(LDAAuthError, match="Authentication failed"):
            client.list_data_assets()

    def test_raises_without_credentials(self):
        with pytest.raises(LDAAuthError, match="must be set"):
            LDAClient(client_id="", client_secret="")

    def test_retries_on_401_response(self):
        client = _make_client()
        client._http.post = MagicMock(side_effect=[
            _token_response(FAKE_TOKEN),
            _token_response(NEW_TOKEN),
        ])
        unauthorized = _error_response(401)
        unauthorized.raise_for_status = MagicMock()
        success = _ok_response({"data_assets": []})
        client._http.request = MagicMock(side_effect=[unauthorized, success])

        result = client.list_data_assets()

        assert result == {"data_assets": []}
        assert client._http.request.call_count == 2
        assert client._http.post.call_count == 2  # initial auth + re-auth after 401


class TestLDAClientMethods:
    def setup_method(self):
        self.client = _make_client()
        self.client._token = FAKE_TOKEN
        self.client._token_obtained_at = time.time()

    def test_list_data_assets(self):
        self.client._http.request = MagicMock(
            return_value=_ok_response({"data_assets": [{"modul": "Aktionsmodul Arbeitsrecht"}]})
        )
        result = self.client.list_data_assets()
        assert result["data_assets"][0]["modul"] == "Aktionsmodul Arbeitsrecht"
        self.client._http.request.assert_called_once_with(
            "GET", "https://fake-lda.example.com/api/data-assets",
            headers=self.client._headers(),
        )

    def test_semantic_search_sends_correct_body(self):
        self.client._http.request = MagicMock(
            return_value=_ok_response({"documents": []})
        )
        self.client.semantic_search("what is Kündigung?", "Aktionsmodul Arbeitsrecht", candidates=5)

        _, kwargs = self.client._http.request.call_args
        body = kwargs["json"]
        assert body["search_query"] == "what is Kündigung?"
        assert body["data_asset"] == "Aktionsmodul Arbeitsrecht"
        assert body["candidates"] == 5
        assert body["post_reranking"] is True

    def test_semantic_search_caps_candidates_at_20(self):
        self.client._http.request = MagicMock(return_value=_ok_response({"documents": []}))
        self.client.semantic_search("query", "asset", candidates=99)

        _, kwargs = self.client._http.request.call_args
        assert kwargs["json"]["candidates"] == 20

    def test_qna_sends_correct_body(self):
        self.client._http.request = MagicMock(
            return_value=_ok_response({"answer": "Yes.", "response_id": "abc", "sourcedocuments": []})
        )
        self.client.qna("Can I terminate without notice?", "Aktionsmodul Arbeitsrecht")

        _, kwargs = self.client._http.request.call_args
        body = kwargs["json"]
        assert body["prompt"] == "Can I terminate without notice?"
        assert body["data_asset"] == "Aktionsmodul Arbeitsrecht"
        assert body["mode"] == "attribution"
        assert body["filter"] == []

    def test_clause_check_sends_correct_body(self):
        self.client._http.request = MagicMock(
            return_value=_ok_response({"answer": "Valid.", "id": "xyz", "sourcedocuments": []})
        )
        self.client.clause_check("The employee may not compete.", "Aktionsmodul Arbeitsrecht")

        _, kwargs = self.client._http.request.call_args
        body = kwargs["json"]
        assert body["prompt"] == "The employee may not compete."
        assert body["mode"] == "check"
        assert body["filter"] == []

    def test_qna_with_filters(self):
        self.client._http.request = MagicMock(return_value=_ok_response({"answer": ""}))
        filters = [{"term": {"metadata.dokumententyp.keyword": "Urteil"}}]
        self.client.qna("question", "asset", filters=filters)

        _, kwargs = self.client._http.request.call_args
        assert kwargs["json"]["filter"] == filters
