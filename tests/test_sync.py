import hashlib
import io
from pathlib import Path
import zipfile

import pytest

import backend.sync as sync_module
from backend.models import GameProfile
from backend.sync import (
    SaveSyncService,
    SyncError,
    build_directory_manifest,
    calc_hash,
    manifest_digest,
    snapshot_path,
)


def test_build_directory_manifest_captures_all_files(tmp_path: Path) -> None:
    save_dir = tmp_path / "save"
    (save_dir / "slot1").mkdir(parents=True)
    (save_dir / "player.dat").write_text("a", encoding="utf-8")
    (save_dir / "slot1" / "world.dat").write_text("b", encoding="utf-8")

    manifest = build_directory_manifest(save_dir)

    assert set(manifest) == {"player.dat", "slot1/world.dat"}


def test_snapshot_path_changes_when_any_directory_file_changes(tmp_path: Path) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "a.sav").write_text("first", encoding="utf-8")
    (save_dir / "b.sav").write_text("second", encoding="utf-8")

    initial = snapshot_path(save_dir)
    (save_dir / "b.sav").write_text("changed", encoding="utf-8")

    assert snapshot_path(save_dir) != initial


def test_snapshot_path_changes_when_directory_file_is_removed(tmp_path: Path) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "a.sav").write_text("first", encoding="utf-8")
    (save_dir / "b.sav").write_text("second", encoding="utf-8")

    initial = snapshot_path(save_dir)
    (save_dir / "b.sav").unlink()

    assert snapshot_path(save_dir) != initial


def test_snapshot_path_changes_when_directory_file_is_added(tmp_path: Path) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "a.sav").write_text("first", encoding="utf-8")

    initial = snapshot_path(save_dir)
    (save_dir / "b.sav").write_text("second", encoding="utf-8")

    assert snapshot_path(save_dir) != initial


def test_build_directory_manifest_rejects_non_directory(tmp_path: Path) -> None:
    save_file = tmp_path / "save.sav"
    save_file.write_text("data", encoding="utf-8")

    with pytest.raises(SyncError):
        build_directory_manifest(save_file)


def test_manifest_digest_is_stable_for_same_manifest() -> None:
    manifest = {"a.sav": "1", "dir/b.sav": "2"}
    reordered = {"dir/b.sav": "2", "a.sav": "1"}
    assert manifest_digest(manifest) == manifest_digest(reordered)


def test_launch_game_opens_steam_uri_for_numeric_game_id(monkeypatch, tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Steam Game",
        game_exe_path="2646460",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )
    launched: list[str] = []

    monkeypatch.setattr(service, "_open_steam_uri", lambda uri: launched.append(uri))

    process = service._launch_game(profile)

    assert process is None
    assert launched == ["steam://rungameid/2646460"]


def test_wait_for_game_launch_requires_detectable_process_for_steam_profile(
    monkeypatch, tmp_path: Path
) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Steam Game",
        game_exe_path="2646460",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )

    tick = {"value": 0}

    def fake_monotonic() -> int:
        tick["value"] += 1
        return tick["value"]

    monkeypatch.setattr(service, "_any_game_process_running", lambda profile: False)
    monkeypatch.setattr(sync_module.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(sync_module.time, "sleep", lambda _: None)

    assert service._wait_for_game_launch(profile, None) is False


class DummyDrive:
    def __init__(self) -> None:
        self.created_metadata: dict | None = None
        self.created_file = DummyDriveFile()

    def CreateFile(self, metadata: dict):
        self.created_metadata = metadata
        return self.created_file


class DummyDriveFile(dict):
    pass


class UploadDriveFile(dict):
    def __init__(self, *, fail_on_upload: bool = False) -> None:
        super().__init__()
        self.fail_on_upload = fail_on_upload
        self.content = None
        self.uploaded_path: Path | None = None

    def SetContentFile(self, filename: str) -> None:
        self.uploaded_path = Path(filename)
        self.content = open(filename, "rb")

    def Upload(self) -> None:
        if self.fail_on_upload:
            raise RuntimeError("upload failed")
        if self.content is None:
            raise AssertionError("Expected open upload content")


class DownloadDrive:
    def __init__(self, remote_file) -> None:
        self.remote_file = remote_file
        self.query: dict | None = None

    def ListFile(self, query: dict):
        self.query = query
        return DownloadListResult(self.remote_file)


class DownloadListResult:
    def __init__(self, remote_file) -> None:
        self.remote_file = remote_file

    def GetList(self):
        if self.remote_file is None:
            return []
        return [self.remote_file]


class RemoteArchiveFile(dict):
    def __init__(
        self, files: dict[str, bytes], *, modified_date: str = "2100-01-01T00:00:00.000Z"
    ) -> None:
        super().__init__()
        self.archive_bytes = build_archive_bytes(files)
        self.download_calls = 0
        self["modifiedDate"] = modified_date

    def GetContentFile(self, filename: str) -> None:
        self.download_calls += 1
        Path(filename).write_bytes(self.archive_bytes)


def build_archive_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, content in sorted(files.items()):
            archive.writestr(relative_path, content)
    return buffer.getvalue()


def write_directory_files(root: Path, files: dict[str, bytes]) -> None:
    for relative_path, content in files.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)


def test_calc_hash_matches_sha256_for_large_file(tmp_path: Path) -> None:
    payload = (b"SaveSync-Chunked-Hash" * 131072) + b"tail"
    save_file = tmp_path / "large.sav"
    save_file.write_bytes(payload)

    assert calc_hash(save_file) == hashlib.sha256(payload).hexdigest()


def test_download_if_needed_skips_replace_when_remote_matches_local(
    tmp_path: Path, monkeypatch
) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    files = {"slot1.sav": b"same-content"}
    write_directory_files(save_folder, files)
    expected_hash = snapshot_path(save_folder)
    drive = DownloadDrive(RemoteArchiveFile(files))
    backups: list[Path] = []
    replacements: list[tuple[Path, Path]] = []

    monkeypatch.setattr(service, "_backup_existing", lambda folder: backups.append(folder))
    monkeypatch.setattr(
        service,
        "_replace_directory",
        lambda target, source: replacements.append((target, source)),
    )

    local_hash, cloud_hash, remote_file = service._download_if_needed(drive, profile, save_folder)

    assert local_hash == expected_hash
    assert cloud_hash == expected_hash
    assert remote_file is drive.remote_file
    assert drive.remote_file.download_calls == 1
    assert backups == []
    assert replacements == []


def test_download_if_needed_backs_up_and_replaces_changed_remote_once(
    tmp_path: Path, monkeypatch
) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    local_files = {"slot1.sav": b"old-content"}
    remote_files = {
        "slot1.sav": b"new-content",
        "slot2/world.sav": b"world-state",
    }
    write_directory_files(save_folder, local_files)
    old_manifest = build_directory_manifest(save_folder)
    drive = DownloadDrive(RemoteArchiveFile(remote_files))
    backups: list[dict[str, str]] = []
    original_snapshot_path = sync_module.snapshot_path
    local_snapshot_calls: list[Path] = []

    def record_backup(folder: Path) -> None:
        backups.append(build_directory_manifest(folder))

    def track_snapshot(path: Path) -> str | None:
        if path == save_folder:
            local_snapshot_calls.append(path)
        return original_snapshot_path(path)

    monkeypatch.setattr(service, "_backup_existing", record_backup)
    monkeypatch.setattr(sync_module, "snapshot_path", track_snapshot)
    monkeypatch.setattr(service, "_latest_tree_mtime", lambda path: 1_000_000_000.0)

    local_hash, cloud_hash, remote_file = service._download_if_needed(drive, profile, save_folder)

    assert remote_file is drive.remote_file
    assert drive.remote_file.download_calls == 1
    assert backups == [old_manifest]
    assert len(local_snapshot_calls) == 1
    assert save_folder.joinpath("slot1.sav").read_bytes() == b"new-content"
    assert save_folder.joinpath("slot2/world.sav").read_bytes() == b"world-state"
    assert local_hash == cloud_hash == original_snapshot_path(save_folder)


def test_download_if_needed_keeps_local_save_when_it_is_newer_than_remote(
    tmp_path: Path, monkeypatch
) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    local_files = {"slot1.sav": b"local-newer"}
    remote_files = {"slot1.sav": b"remote-older"}
    write_directory_files(save_folder, local_files)
    drive = DownloadDrive(
        RemoteArchiveFile(remote_files, modified_date="2024-01-01T00:00:00.000Z")
    )
    backups: list[Path] = []
    replacements: list[tuple[Path, Path]] = []
    expected_local_hash = snapshot_path(save_folder)
    expected_cloud_root = tmp_path / "expected-cloud"
    expected_cloud_root.mkdir()
    write_directory_files(expected_cloud_root, remote_files)
    expected_cloud_hash = snapshot_path(expected_cloud_root)

    monkeypatch.setattr(service, "_latest_tree_mtime", lambda path: 1_800_000_000.0)
    monkeypatch.setattr(service, "_backup_existing", lambda folder: backups.append(folder))
    monkeypatch.setattr(
        service,
        "_replace_directory",
        lambda target, source: replacements.append((target, source)),
    )

    local_hash, cloud_hash, remote_file = service._download_if_needed(drive, profile, save_folder)

    assert remote_file is drive.remote_file
    assert cloud_hash == expected_cloud_hash
    assert local_hash == expected_local_hash
    assert local_hash != cloud_hash
    assert backups == []
    assert replacements == []
    assert save_folder.joinpath("slot1.sav").read_bytes() == b"local-newer"


def test_upload_if_needed_uploads_unchanged_local_save_when_cloud_is_older(tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("local-newer", encoding="utf-8")
    meta_path = tmp_path / "save.meta.json"
    existing_file = DummyDriveFile(title="save.zip")
    uploaded: list[DummyDriveFile] = []

    service._upload_directory = lambda drive_file, folder: uploaded.append(drive_file)

    final_hash = snapshot_path(save_folder)
    service._upload_if_needed(
        drive=None,
        profile=profile,
        save_folder=save_folder,
        meta_path=meta_path,
        initial_hash=final_hash,
        final_hash=final_hash,
        cloud_hash="older-cloud-hash",
        remote_file=existing_file,
    )

    assert uploaded == [existing_file]


def test_upload_if_needed_creates_initial_remote_archive_without_local_changes(tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="save",
        drive_folder_id="folder-123",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("same-content", encoding="utf-8")
    meta_path = tmp_path / "save.meta.json"
    drive = DummyDrive()
    uploaded: list[tuple[DummyDriveFile, Path]] = []

    service._upload_directory = lambda drive_file, folder: uploaded.append((drive_file, folder))

    final_hash = snapshot_path(save_folder)
    service._upload_if_needed(
        drive,
        profile,
        save_folder,
        meta_path,
        initial_hash=final_hash,
        final_hash=final_hash,
        cloud_hash=None,
        remote_file=None,
    )

    assert drive.created_metadata == {
        "title": "save.zip",
        "parents": [{"id": "folder-123"}],
    }
    assert uploaded == [(drive.created_file, save_folder)]
    assert meta_path.exists()


def test_upload_if_needed_updates_existing_remote_file_metadata(tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    profile = GameProfile.create(
        display_name="Example Game",
        game_exe_path="C:/Games/Game.exe",
        save_folder_path=str(tmp_path / "save"),
        game_process_names=["Game.exe"],
        drive_filename="fresh-name",
        drive_folder_id="new-folder",
    )
    save_folder = Path(profile.save_folder_path)
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("changed-content", encoding="utf-8")
    meta_path = tmp_path / "save.meta.json"
    existing_file = DummyDriveFile(title="old-name.zip", parents=[{"id": "old-folder"}])
    uploaded: list[DummyDriveFile] = []

    service._upload_directory = lambda drive_file, folder: uploaded.append(drive_file)

    service._upload_if_needed(
        drive=None,
        profile=profile,
        save_folder=save_folder,
        meta_path=meta_path,
        initial_hash="initial",
        final_hash=snapshot_path(save_folder),
        cloud_hash="outdated",
        remote_file=existing_file,
    )

    assert existing_file["title"] == "fresh-name.zip"
    assert existing_file["parents"] == [{"id": "new-folder"}]
    assert uploaded == [existing_file]


def test_upload_directory_closes_drive_content_and_removes_temp_archive(tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    save_folder = tmp_path / "save"
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("data", encoding="utf-8")
    drive_file = UploadDriveFile()

    service._upload_directory(drive_file, save_folder)

    assert drive_file.uploaded_path is not None
    assert drive_file.content is None
    assert not drive_file.uploaded_path.exists()


def test_upload_directory_ignores_locked_temp_archive_cleanup(tmp_path: Path, monkeypatch) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    save_folder = tmp_path / "save"
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("data", encoding="utf-8")
    drive_file = UploadDriveFile()

    def deny_unlink(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("file is locked")

    monkeypatch.setattr(Path, "unlink", deny_unlink)

    service._upload_directory(drive_file, save_folder)

    assert drive_file.uploaded_path is not None
    assert drive_file.content is None
    assert drive_file.uploaded_path.exists()


def test_upload_directory_propagates_upload_errors(tmp_path: Path) -> None:
    service = SaveSyncService(base_dir=tmp_path)
    save_folder = tmp_path / "save"
    save_folder.mkdir()
    (save_folder / "slot1.sav").write_text("data", encoding="utf-8")
    drive_file = UploadDriveFile(fail_on_upload=True)

    with pytest.raises(RuntimeError, match="upload failed"):
        service._upload_directory(drive_file, save_folder)

    assert drive_file.content is None
