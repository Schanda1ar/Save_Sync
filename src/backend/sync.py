from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

import psutil

from .google_drive import GoogleDriveClient
from .models import GameProfile

StatusCallback = Callable[[str], None]


class SyncError(RuntimeError):
    """Raised when sync or launch workflow fails."""


def calc_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class SaveSyncService:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self.drive_client = GoogleDriveClient(base_dir=base_dir)

    def run_profile(self, profile: GameProfile, status: StatusCallback | None = None) -> None:
        report = status or (lambda _: None)
        save_path = Path(profile.save_file_path)
        game_exe = Path(profile.game_exe_path)
        meta_path = save_path.with_suffix(".meta.json")

        if not game_exe.exists():
            raise SyncError(f"Spiel-Executable nicht gefunden: {game_exe}")
        if save_path.exists() and not save_path.is_file():
            raise SyncError(f"Save-Pfad ist keine Datei: {save_path}")

        report("Authentifizierung läuft")
        drive = self.drive_client.build_drive()

        report("Download läuft")
        initial_hash, cloud_hash, remote_file = self._download_if_needed(drive, profile, save_path)

        report("Spielstart")
        process = subprocess.Popen([str(game_exe)], shell=False)
        self._wait_for_game(profile, process, report)

        report("Upload läuft")
        final_hash = calc_hash(save_path)
        self._upload_if_needed(
            drive,
            profile,
            save_path,
            meta_path,
            initial_hash,
            final_hash,
            cloud_hash,
            remote_file,
        )
        report("Abgeschlossen")

    def _query(self, profile: GameProfile) -> str:
        filename = profile.drive_filename.replace("'", "\\'")
        if profile.drive_folder_id:
            return (
                f"'{profile.drive_folder_id}' in parents and title='{filename}' and trashed=false"
            )
        return f"title='{filename}' and trashed=false"

    def _download_if_needed(self, drive, profile: GameProfile, save_path: Path):
        file_list = drive.ListFile({"q": self._query(profile)}).GetList()
        remote_file = file_list[0] if file_list else None
        local_hash = calc_hash(save_path)
        cloud_hash = None

        if remote_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=save_path.suffix) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                remote_file.GetContentFile(str(temp_path))
                cloud_hash = calc_hash(temp_path)
            finally:
                if temp_path.exists():
                    temp_path.unlink()

        if cloud_hash and cloud_hash != local_hash:
            if save_path.exists():
                backup_name = f"{save_path.stem}_backup_{int(time.time())}{save_path.suffix}"
                backup_path = save_path.with_name(backup_name)
                shutil.copy2(save_path, backup_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            remote_file.GetContentFile(str(save_path))
            local_hash = calc_hash(save_path)

        return local_hash, cloud_hash, remote_file

    def _upload_if_needed(
        self,
        drive,
        profile: GameProfile,
        save_path: Path,
        meta_path: Path,
        initial_hash: str | None,
        final_hash: str | None,
        cloud_hash: str | None,
        remote_file,
    ) -> None:
        if final_hash is None:
            raise SyncError(f"Save-Datei nicht gefunden: {save_path}")
        if final_hash == initial_hash:
            return
        if cloud_hash and final_hash == cloud_hash:
            return

        drive_file = remote_file
        if drive_file is None:
            metadata = {"title": profile.drive_filename}
            if profile.drive_folder_id:
                metadata["parents"] = [{"id": profile.drive_folder_id}]
            drive_file = drive.CreateFile(metadata)

        drive_file.SetContentFile(str(save_path))
        drive_file.Upload()
        meta_path.write_text(f'{{"hash": "{final_hash}"}}', encoding="utf-8")

    def _wait_for_game(
        self,
        profile: GameProfile,
        process: subprocess.Popen,
        report: StatusCallback,
    ) -> None:
        report("Spiel läuft")
        time.sleep(3)
        while True:
            if process.poll() is not None and not self._any_game_process_running(profile):
                break
            if self._any_game_process_running(profile):
                time.sleep(2)
                continue
            if process.poll() is not None:
                break
            time.sleep(2)

    def _any_game_process_running(self, profile: GameProfile) -> bool:
        names = {name.lower() for name in profile.game_process_names}
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in names:
                return True
        return False
