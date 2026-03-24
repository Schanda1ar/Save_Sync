from __future__ import annotations

from pathlib import Path

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from .app_paths import client_secrets_path, credentials_path


class GoogleDriveAuthError(RuntimeError):
    """Raised when Google Drive authorization fails."""


class GoogleDriveClient:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir
        self._credentials_path = credentials_path()
        self._client_secrets_path = client_secrets_path(base_dir)

    def build_drive(self) -> GoogleDrive:
        gauth = self._build_auth()
        return GoogleDrive(gauth)

    def _build_auth(self) -> GoogleAuth:
        if not self._client_secrets_path.exists():
            raise GoogleDriveAuthError(
                f"client_secrets.json nicht gefunden: {self._client_secrets_path}"
            )

        gauth = GoogleAuth()
        gauth.LoadClientConfigFile(str(self._client_secrets_path))
        gauth.settings["get_refresh_token"] = True
        gauth.settings["access_type"] = "offline"
        gauth.settings["prompt"] = "consent"

        if self._credentials_path.exists():
            gauth.LoadCredentialsFile(str(self._credentials_path))

        if gauth.credentials is None:
            self._interactive_login(gauth)
            return gauth

        if gauth.access_token_expired:
            try:
                gauth.Refresh()
                gauth.SaveCredentialsFile(str(self._credentials_path))
                return gauth
            except Exception:
                self._interactive_login(gauth)
                return gauth

        try:
            gauth.Authorize()
        except Exception:
            if gauth.credentials is not None:
                try:
                    gauth.Refresh()
                    gauth.SaveCredentialsFile(str(self._credentials_path))
                    return gauth
                except Exception:
                    self._interactive_login(gauth)
                    return gauth
            self._interactive_login(gauth)
        return gauth

    def _interactive_login(self, gauth: GoogleAuth) -> None:
        try:
            gauth.credentials = None
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile(str(self._credentials_path))
        except Exception as exc:
            raise GoogleDriveAuthError(f"Google-Anmeldung fehlgeschlagen: {exc}") from exc
