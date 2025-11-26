from pathlib import Path

import pytest

from nipoppy.utils import fileops


class TestRemoveExistingPath:
    def test_rm_file(self, tmp_path: Path):
        """Test _remove_existing removes regular files."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")
        fileops._remove_existing(test_file)
        assert not test_file.exists()

    def test_rm_directory(self, tmp_path: Path):
        """Test _remove_existing removes directories."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "nested_file.txt").write_text("content")
        fileops._remove_existing(test_dir)
        assert not test_dir.exists()

    def test_rm_symlink_to_file(self, tmp_path: Path):
        """Test _remove_existing removes symlinks to files."""
        target_file = tmp_path / "target.txt"
        target_file.write_text("content")

        symlink = tmp_path / "link_to_file"
        symlink.symlink_to(target_file)

        fileops._remove_existing(symlink)

        assert not symlink.exists()
        assert target_file.exists()  # Target should remain

    def test_rm_symlink_to_directory(self, tmp_path: Path):
        """Test _remove_existing removes symlinks to directories."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()

        symlink = tmp_path / "link_to_dir"
        symlink.symlink_to(target_dir)

        fileops._remove_existing(symlink)

        assert not symlink.exists()
        assert target_dir.exists()  # Target should remain

    def test_rm_surfaces_permission_error(self, tmp_path: Path):
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

    def test_rm_broken_symlink(self, tmp_path: Path):
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


class TestMakeDir:
    def test_mkdir_creates_directory(self, tmp_path: Path):
        """Test mkdir creates a new directory."""
        new_dir = tmp_path / "new_directory"
        fileops.mkdir(new_dir)
        assert new_dir.is_dir()

    def test_mkdir_existing_directory(self, tmp_path: Path):
        """Test mkdir does not raise an error if the directory already exists."""
        existing_dir = tmp_path / "existing_directory"
        existing_dir.mkdir()
        fileops.mkdir(existing_dir)  # Should not raise
        assert existing_dir.is_dir()

    def test_mkdir_existing_file_raises(self, tmp_path: Path):
        """Test mkdir raises FileOperationError if path exists as a file."""
        existing_file = tmp_path / "existing_file.txt"
        existing_file.touch()
        with pytest.raises(fileops.FileOperationError):
            fileops.mkdir(existing_file)


class TestCopy:
    def test_copy_file(self, tmp_path: Path):
        """Test copying a file."""
        source_file = tmp_path / "source.txt"
        EXPECTED_CONTENT = "content"
        source_file.write_text(EXPECTED_CONTENT)
        dest_file = tmp_path / "dest.txt"

        fileops.copy(source_file, dest_file)

        assert dest_file.is_file()
        assert dest_file.read_text() == EXPECTED_CONTENT

    def test_copy_directory(self, tmp_path: Path):
        """Test copying a directory."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("file1 content")
        (source_dir / "file2.txt").write_text("file2 content")

        dest_dir = tmp_path / "dest_dir"

        fileops.copy(source_dir, dest_dir)

        assert dest_dir.is_dir()
        assert (dest_dir / "file1.txt").read_text() == "file1 content"
        assert (dest_dir / "file2.txt").read_text() == "file2 content"


class TestMoveTree:
    def test_movetree_directory(self, tmp_path: Path):
        """Test moving a directory tree."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("file1 content")
        (source_dir / "file2.txt").write_text("file2 content")

        dest_dir = tmp_path / "dest_dir"

        fileops.movetree(source_dir, dest_dir)

        assert dest_dir.is_dir()
        assert (dest_dir / "file1.txt").read_text() == "file1 content"
        assert (dest_dir / "file2.txt").read_text() == "file2 content"
        assert not source_dir.exists()


class TestSymlinkTo:
    def test_symlink_to(self, tmp_path: Path):
        """Test creating a symlink to a file."""
        target_file = tmp_path / "target.txt"
        EXPECTED_CONTENT = "target content"
        target_file.write_text(EXPECTED_CONTENT)

        symlink = tmp_path / "symlink_to_target"

        fileops.symlink_to(target_file, symlink)

        assert symlink.is_symlink()
        assert symlink.read_text() == EXPECTED_CONTENT


class TestRemove:
    def test_rm_file(self, tmp_path: Path):
        """Test removing a file."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")
        fileops.rm(test_file)
        assert not test_file.exists()

    def test_rm_directory(self, tmp_path: Path):
        """Test removing a directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "nested_file.txt").write_text("content")
        fileops.rm(test_dir)
        assert not test_dir.exists()
