from pathlib import Path

import pytest

from nipoppy.utils import fileops


def test_remove_existing_file(tmp_path: Path):
    """Test _remove_existing removes regular files."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("content")
    fileops._remove_existing(test_file)
    assert not test_file.exists()


def test_remove_existing_directory(tmp_path: Path):
    """Test _remove_existing removes directories."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "nested_file.txt").write_text("content")
    fileops._remove_existing(test_dir)
    assert not test_dir.exists()


def test_remove_existing_symlink_to_file(tmp_path: Path):
    """Test _remove_existing removes symlinks to files."""
    target_file = tmp_path / "target.txt"
    target_file.write_text("content")

    symlink = tmp_path / "link_to_file"
    symlink.symlink_to(target_file)

    fileops._remove_existing(symlink)

    assert not symlink.exists()
    assert target_file.exists()  # Target should remain


def test_remove_existing_symlink_to_directory(tmp_path: Path):
    """Test _remove_existing removes symlinks to directories."""
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    symlink = tmp_path / "link_to_dir"
    symlink.symlink_to(target_dir)

    fileops._remove_existing(symlink)

    assert not symlink.exists()
    assert target_dir.exists()  # Target should remain


def test_remove_existing_surfaces_permission_error(tmp_path: Path):
    """Test _remove_existing surfaces permission errors instead of ignoring them."""
    # Create a directory with a file, then make it read-only
    test_dir = tmp_path / "readonly_dir"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("content")

    # Make directory read-only (no write/execute permissions)
    test_dir.chmod(0o444)

    try:
        with pytest.raises(PermissionError):
            fileops._remove_existing(test_dir)
    finally:
        # Cleanup: restore permissions so test cleanup works
        test_dir.chmod(0o755)


def test_remove_existing_broken_symlink(tmp_path: Path):
    """Test _remove_existing handles broken symlinks."""
    nonexistent_target = tmp_path / "does_not_exist.txt"
    broken_symlink = tmp_path / "broken_link"
    broken_symlink.symlink_to(nonexistent_target)

    # Verify it's actually broken
    assert broken_symlink.is_symlink()
    assert not broken_symlink.exists()

    fileops._remove_existing(broken_symlink)

    assert not broken_symlink.is_symlink()
    assert not broken_symlink.exists()
