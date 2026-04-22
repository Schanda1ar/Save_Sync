from pathlib import Path

from backend.models import normalize_save_folder_path


def test_normalize_save_folder_path_preserves_missing_dotted_directory_name() -> None:
    path_text = str(Path("C:/Saves/save.v2"))

    assert normalize_save_folder_path(path_text) == path_text


def test_normalize_save_folder_path_preserves_missing_file_like_input_as_folder_path() -> None:
    """Save sources are modeled only as folders, so missing paths stay untouched."""
    path_text = str(Path("C:/Saves/slot1.sav"))

    assert normalize_save_folder_path(path_text) == path_text
