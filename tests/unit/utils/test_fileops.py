import errno
from contextlib import nullcontext
from pathlib import Path

import pytest
import pytest_mock

from nipoppy.exceptions import FileOperationError
from nipoppy.utils import fileops


def create_dummy_directory_structure(base_path: Path):
    """Create a dummy directory structure for testing."""
    (base_path / "subdir1").mkdir(parents=True)
    (base_path / "subdir1" / "file1.txt").write_text("This is file 1.")
    (base_path / "subdir1" / "file2.txt").write_text("This is file 2.")
    (base_path / "subdir2").mkdir(parents=True)
    (base_path / "subdir2" / "file3.txt").write_text("This is file 3.")


def check_dummy_directory_structure(base_path: Path):
    """Check the dummy directory structure for testing."""
    assert (base_path / "subdir1").is_dir()
    assert (base_path / "subdir1" / "file1.txt").read_text() == "This is file 1."
    assert (base_path / "subdir1" / "file2.txt").read_text() == "This is file 2."
    assert (base_path / "subdir2").is_dir()
    assert (base_path / "subdir2" / "file3.txt").read_text() == "This is file 3."


class TestRemovePath:
    def test_rm_file(self, tmp_path: Path):
        """Test removing regular files."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")
        fileops.rm(test_file)
        assert not test_file.exists()

    def test_rm_directory(self, tmp_path: Path):
        """Test removing directories."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "nested_file.txt").write_text("content")
        fileops.rm(test_dir)
        assert not test_dir.exists()

    def test_rm_symlink_to_file(self, tmp_path: Path):
        """Test removing symlinks to files."""
        target_file = tmp_path / "target.txt"
        target_file.write_text("content")

        symlink = tmp_path / "link_to_file"
        symlink.symlink_to(target_file)

        fileops.rm(symlink)

        assert not symlink.exists()
        assert target_file.exists()  # Target should remain

    def test_rm_symlink_to_directory(self, tmp_path: Path):
        """Test removing symlinks to directories."""
        target_dir = tmp_path / "target_dir"
        target_dir.mkdir()

        symlink = tmp_path / "link_to_dir"
        symlink.symlink_to(target_dir)

        fileops.rm(symlink)

        assert not symlink.exists()
        assert target_dir.exists()  # Target should remain

    def test_rm_surfaces_permission_error(self, tmp_path: Path):
        """Test surfacing permission errors instead of ignoring them."""
        # Create a directory with a file, then make it read-only
        test_dir = tmp_path / "readonly_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        # Make directory read-only (no write/execute permissions)
        test_dir.chmod(0o444)

        try:
            with pytest.raises(PermissionError):
                fileops.rm(test_dir)
        finally:
            # Cleanup: restore permissions so test cleanup works
            test_dir.chmod(0o755)

    def test_rm_broken_symlink(self, tmp_path: Path):
        """Test handling broken symlinks."""
        nonexistent_target = tmp_path / "does_not_exist.txt"
        broken_symlink = tmp_path / "broken_link"
        broken_symlink.symlink_to(nonexistent_target)

        # Verify it's actually broken
        assert broken_symlink.is_symlink()
        assert not broken_symlink.exists()

        fileops.rm(broken_symlink)

        assert not broken_symlink.is_symlink()
        assert not broken_symlink.exists()

    def test_rm_ignores_non_empty_directory_error(
        self, tmp_path: Path, mocker: pytest_mock.MockerFixture
    ):
        """Test that OSError 'Directory not empty' is ignored."""
        # os.rmdir is called by shutil.rmtree internally when removing directories
        mocked_rmdir = mocker.patch(
            "os.rmdir",
            side_effect=OSError(errno.ENOTEMPTY, errno.errorcode[errno.ENOTEMPTY]),
        )

        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        # should not raise error
        fileops.rm(test_dir)

        mocked_rmdir.assert_called_once()
        assert next(test_dir.iterdir(), None) is None  # file was removed
        assert test_dir.exists()  # directory was not removed

    def test_rm_non_empty_directory(self, tmp_path: Path):
        """Test that non-empty directories are removed successfully."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        # should not raise error
        fileops.rm(test_dir)

        assert not test_dir.exists()


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
    @pytest.mark.parametrize(
        "exist_ok, raises_error, final_content",
        [
            (True, False, "content"),
            (False, True, "old content"),
        ],
    )
    def test_cp_file(self, tmp_path: Path, exist_ok, raises_error, final_content):
        """Test copying a file."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("content")

        dest_file = tmp_path / "dest.txt"
        dest_file.write_text("old content")

        with pytest.raises(FileOperationError) if raises_error else nullcontext():
            fileops.copy(source_file, dest_file, exist_ok=exist_ok)

        assert dest_file.is_file()
        assert dest_file.read_text() == final_content

    @pytest.mark.parametrize(
        "exist_ok, raises_error, dest_should_be_empty",
        [
            (True, False, False),
            (False, True, True),
        ],
    )
    def test_cp_dir(self, tmp_path: Path, exist_ok, raises_error, dest_should_be_empty):
        """Test copying a directory."""
        source_dir = tmp_path / "source_dir"
        dest_dir = tmp_path / "dest_dir"
        create_dummy_directory_structure(source_dir)
        dest_dir.mkdir()  # Pre-create destination directory

        with pytest.raises(FileOperationError) if raises_error else nullcontext():
            fileops.copy(source_dir, dest_dir, exist_ok=exist_ok)

        if dest_should_be_empty:
            # Ensure destination directory is unchanged (empty)
            assert not any(dest_dir.iterdir())
        else:
            check_dummy_directory_structure(dest_dir)


class TestMoveTree:
    # Should we add an exist_ok test here too?
    def test_mv_directory(self, tmp_path: Path):
        """Test moving a directory tree."""
        source_dir = tmp_path / "source_dir"
        dest_dir = tmp_path / "dest_dir"
        create_dummy_directory_structure(source_dir)

        fileops.movetree(source_dir, dest_dir)
        check_dummy_directory_structure(dest_dir)
        assert not source_dir.exists()


class TestSymlink:
    # Should we add an exist_ok test here too?
    def test_symlink(self, tmp_path: Path):
        """Test creating a symlink to a file."""
        source_file = tmp_path / "target.txt"
        expected_content = "target content"
        source_file.write_text(expected_content)

        symlink = tmp_path / "symlink_to_target"

        fileops.symlink(source=source_file, target=symlink)

        assert symlink.is_symlink()
        assert symlink.read_text() == expected_content
