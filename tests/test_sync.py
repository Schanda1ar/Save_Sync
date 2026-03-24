from pathlib import Path

import pytest

from backend.sync import SyncError, build_directory_manifest, manifest_digest, snapshot_path


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
