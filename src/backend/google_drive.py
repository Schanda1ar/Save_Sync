from __future__ import annotations

from pathlib import Path
from typing import Callable

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from .app_paths import client_secrets_path, credentials_path

StatusCallback = Callable[[str], None]


class GoogleDriveAuthError(RuntimeError):
    """Raised when Google Drive authorization fails."""


class GoogleDriveClient:
    """Create authenticated Google Drive clients with credential fallback handling."""

    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir
        self._credentials_path = credentials_path()
        self._client_secrets_path = client_secrets_path(base_dir)

    def build_drive(self, *, status: StatusCallback | None = None) -> GoogleDrive:
        """Build an authenticated Google Drive instance and report auth sub-steps."""
        report = status or (lambda _: None)
        gauth = self._build_auth(status=report)
        return GoogleDrive(gauth)

    def _build_auth(self, *, status: StatusCallback | None = None) -> GoogleAuth:
        """Load, refresh, or recreate OAuth credentials as needed."""
        report = status or (lambda _: None)
        report("Google-Authentifizierung wird vorbereitet")
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
            report("Gespeicherte Anmeldedaten werden geladen")
            gauth.LoadCredentialsFile(str(self._credentials_path))

        if gauth.credentials is None:
            self._interactive_login(gauth, status=report)
            report("Google-Authentifizierung abgeschlossen")
            return gauth

        report("Token wird geprüft")
        if gauth.access_token_expired:
            try:
                report("Token wird erneuert")
                gauth.Refresh()
                gauth.SaveCredentialsFile(str(self._credentials_path))
                report("Google-Authentifizierung abgeschlossen")
                return gauth
            except Exception:
                # A failed refresh usually means the cached token is no longer usable.
                self._interactive_login(gauth, status=report)
                report("Google-Authentifizierung abgeschlossen")
                return gauth

        try:
            gauth.Authorize()
        except Exception:
            if gauth.credentials is not None:
                try:
                    report("Token wird erneuert")
                    gauth.Refresh()
                    gauth.SaveCredentialsFile(str(self._credentials_path))
                    report("Google-Authentifizierung abgeschlossen")
                    return gauth
                except Exception:
                    self._interactive_login(gauth, status=report)
                    report("Google-Authentifizierung abgeschlossen")
                    return gauth
            self._interactive_login(gauth, status=report)
        report("Google-Authentifizierung abgeschlossen")
        return gauth

    def _interactive_login(
        self, gauth: GoogleAuth, *, status: StatusCallback | None = None
    ) -> None:
        """Run the browser-based OAuth flow and persist the resulting credentials."""
        report = status or (lambda _: None)
        try:
            report("Browser-Anmeldung wird gestartet")
            gauth.credentials = None
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile(str(self._credentials_path))
        except Exception as exc:
            raise GoogleDriveAuthError(f"Google-Anmeldung fehlgeschlagen: {exc}") from exc
