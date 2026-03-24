from pathlib import Path

import pytest

import backend.sync as sync_module
from backend.models import GameProfile
from backend.sync import SaveSyncService, SyncError, build_directory_manifest, manifest_digest, snapshot_path


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
