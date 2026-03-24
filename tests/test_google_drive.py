from pathlib import Path

import pytest

import backend.google_drive as google_drive_module
from backend.google_drive import GoogleDriveAuthError, GoogleDriveClient


class FakeGoogleAuth:
    def __init__(self) -> None:
        self.settings: dict[str, object] = {}
        self.credentials = object()
        self.access_token_expired = False
        self.load_client_config_calls: list[str] = []
        self.load_credentials_calls: list[str] = []
        self.save_credentials_calls: list[str] = []
        self.refresh_exception: Exception | None = None
        self.authorize_exception: Exception | None = None
        self.local_webserver_exception: Exception | None = None
        self.refresh_calls = 0
        self.authorize_calls = 0
        self.local_webserver_calls = 0

    def LoadClientConfigFile(self, path: str) -> None:
        self.load_client_config_calls.append(path)

    def LoadCredentialsFile(self, path: str) -> None:
        self.load_credentials_calls.append(path)

    def SaveCredentialsFile(self, path: str) -> None:
        self.save_credentials_calls.append(path)

    def Refresh(self) -> None:
        self.refresh_calls += 1
        if self.refresh_exception is not None:
            raise self.refresh_exception

    def Authorize(self) -> None:
        self.authorize_calls += 1
        if self.authorize_exception is not None:
            raise self.authorize_exception

    def LocalWebserverAuth(self) -> None:
        self.local_webserver_calls += 1
        if self.local_webserver_exception is not None:
            raise self.local_webserver_exception


def build_client(tmp_path: Path) -> GoogleDriveClient:
    client = GoogleDriveClient(base_dir=tmp_path)
    client._client_secrets_path = tmp_path / "client_secrets.json"
    client._credentials_path = tmp_path / "mycreds.txt"
    return client


def test_build_auth_rejects_missing_client_secrets(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    with pytest.raises(GoogleDriveAuthError, match="client_secrets.json nicht gefunden"):
        client._build_auth()


def test_build_auth_refreshes_expired_token_and_persists_credentials(
    monkeypatch, tmp_path: Path
) -> None:
    client = build_client(tmp_path)
    client._client_secrets_path.write_text("{}", encoding="utf-8")
    client._credentials_path.write_text("token", encoding="utf-8")
    fake_auth = FakeGoogleAuth()
    fake_auth.access_token_expired = True

    monkeypatch.setattr(google_drive_module, "GoogleAuth", lambda: fake_auth)

    result = client._build_auth()

    assert result is fake_auth
    assert fake_auth.refresh_calls == 1
    assert fake_auth.local_webserver_calls == 0
    assert fake_auth.save_credentials_calls == [str(client._credentials_path)]


def test_build_auth_falls_back_to_interactive_login_when_refresh_fails(
    monkeypatch, tmp_path: Path
) -> None:
    client = build_client(tmp_path)
    client._client_secrets_path.write_text("{}", encoding="utf-8")
    client._credentials_path.write_text("token", encoding="utf-8")
    fake_auth = FakeGoogleAuth()
    fake_auth.access_token_expired = True
    fake_auth.refresh_exception = RuntimeError("refresh failed")

    monkeypatch.setattr(google_drive_module, "GoogleAuth", lambda: fake_auth)

    result = client._build_auth()

    assert result is fake_auth
    assert fake_auth.refresh_calls == 1
    assert fake_auth.local_webserver_calls == 1
    assert fake_auth.save_credentials_calls == [str(client._credentials_path)]


def test_build_auth_uses_refresh_after_authorize_failure(monkeypatch, tmp_path: Path) -> None:
    client = build_client(tmp_path)
    client._client_secrets_path.write_text("{}", encoding="utf-8")
    client._credentials_path.write_text("token", encoding="utf-8")
    fake_auth = FakeGoogleAuth()
    fake_auth.authorize_exception = RuntimeError("authorize failed")

    monkeypatch.setattr(google_drive_module, "GoogleAuth", lambda: fake_auth)

    result = client._build_auth()

    assert result is fake_auth
    assert fake_auth.authorize_calls == 1
    assert fake_auth.refresh_calls == 1
    assert fake_auth.local_webserver_calls == 0
    assert fake_auth.save_credentials_calls == [str(client._credentials_path)]


def test_interactive_login_wraps_login_errors(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    fake_auth = FakeGoogleAuth()
    fake_auth.local_webserver_exception = RuntimeError("browser blocked")

    with pytest.raises(GoogleDriveAuthError, match="Google-Anmeldung fehlgeschlagen"):
        client._interactive_login(fake_auth)
