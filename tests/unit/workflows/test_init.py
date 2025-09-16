"""Tests for the dataset init workflow."""

import os
from pathlib import Path

import pytest
from fids import fids

from nipoppy.env import FAKE_SESSION_ID, NIPOPPY_DIR_NAME
from nipoppy.tabular.manifest import Manifest
from nipoppy.utils.utils import DPATH_HPC, DPATH_LAYOUTS
from nipoppy.workflows.dataset_init import InitWorkflow
from tests.conftest import ATTR_TO_DPATH_MAP, FPATH_CONFIG, FPATH_MANIFEST


@pytest.fixture(params=["my_dataset", "dataset_dir"])
def dpath_root(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return tmp_path / request.param


def exist_or_none(o: object, s: str) -> bool:
    # walrus operator ":=" does assignment inside the "if" statement
    if attr := getattr(o, s, None):
        return attr.exists()
    return True


def assert_layout_creation(workflow, dpath_root):
    # check that all directories have been created
    for path in ATTR_TO_DPATH_MAP.values():
        assert Path(dpath_root, path).exists()
        if path == NIPOPPY_DIR_NAME:
            # Nipoppy project directory doesn't have a README file.
            continue
        else:
            assert Path(dpath_root, path, "README.md").exists()

    # check that sample config files have been copied
    assert Path(dpath_root, FPATH_CONFIG).exists()
    assert Path(dpath_root, FPATH_MANIFEST).exists()

    # check that no pipeline config files have been copied
    assert (
        len(
            list(
                workflow.layout.dpath_pipelines.glob(
                    f"**/{workflow.layout.fname_pipeline_config}"
                )
            )
        )
        == 0
    )

    # check that HPC config files have been copied
    for fname in DPATH_HPC.glob("*"):
        assert (workflow.layout.dpath_hpc / fname).exists()


def test_run(dpath_root: Path):
    workflow = InitWorkflow(dpath_root=dpath_root)
    workflow.run()

    assert_layout_creation(workflow, dpath_root)


def test_empty_dir(dpath_root: Path):
    dpath_root.mkdir(parents=True)
    dpath_root.joinpath(".DS_STORE").touch()  # Allow macOS file

    workflow = InitWorkflow(dpath_root=dpath_root)
    workflow.run()

    assert_layout_creation(workflow, dpath_root)


def test_non_empty_dir(dpath_root: Path):
    dpath_root.mkdir(parents=True)
    dpath_root.joinpath("unexepected_file").touch()

    with pytest.raises(FileExistsError, match="Dataset directory is non-empty"):
        workflow = InitWorkflow(dpath_root=dpath_root)
        workflow.run()


def test_non_empty_dir_forced(dpath_root: Path):
    dpath_root.mkdir(parents=True)
    dpath_root.joinpath("unexepected_file").touch()

    workflow = InitWorkflow(dpath_root=dpath_root, force=True)
    workflow.run()


def test_force_with_bids_source_existing_bids_dir(dpath_root: Path, tmp_path: Path):
    """Test --force with --bids-source when BIDS directory already exists."""
    # Create a source BIDS dataset
    bids_source = tmp_path / "source_bids"
    bids_source.mkdir()

    # Create target with existing bids directory
    existing_bids = dpath_root / "bids"
    existing_bids.mkdir(parents=True)
    (existing_bids / "old_file.txt").write_text("old content")

    # Test with force=True - should succeed
    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_source, mode="copy", force=True
    )
    workflow.run()

    # Verify old content was replaced
    assert existing_bids.exists()
    assert not (existing_bids / "old_file.txt").exists()


def test_force_with_bids_source_existing_bids_symlink(dpath_root: Path, tmp_path: Path):
    """Test --force with --bids-source when BIDS symlink already exists."""
    # Create a source BIDS dataset
    bids_source = tmp_path / "source_bids"
    bids_source.mkdir()

    # Create another target for the old symlink
    old_target = tmp_path / "old_bids"
    old_target.mkdir()
    (old_target / "old_file.txt").write_text("old content")

    # Create target with existing bids symlink
    dpath_root.mkdir(parents=True)
    existing_bids_symlink = dpath_root / "bids"
    existing_bids_symlink.symlink_to(old_target)

    # Test with force=True - should succeed
    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_source, mode="symlink", force=True
    )
    workflow.run()

    # Verify old symlink was replaced
    assert existing_bids_symlink.is_symlink()
    assert existing_bids_symlink.resolve() == bids_source.resolve()
    assert old_target.exists()  # Old target should remain


def test_remove_existing_file(tmp_path: Path):
    """Test _remove_existing removes regular files."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("content")

    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow._remove_existing(test_file)

    assert not test_file.exists()


def test_remove_existing_directory(tmp_path: Path):
    """Test _remove_existing removes directories."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "nested_file.txt").write_text("content")

    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow._remove_existing(test_dir)

    assert not test_dir.exists()


def test_remove_existing_symlink_to_file(tmp_path: Path):
    """Test _remove_existing removes symlinks to files."""
    target_file = tmp_path / "target.txt"
    target_file.write_text("content")

    symlink = tmp_path / "link_to_file"
    symlink.symlink_to(target_file)

    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow._remove_existing(symlink)

    assert not symlink.exists()
    assert target_file.exists()  # Target should remain


def test_remove_existing_symlink_to_directory(tmp_path: Path):
    """Test _remove_existing removes symlinks to directories."""
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()

    symlink = tmp_path / "link_to_dir"
    symlink.symlink_to(target_dir)

    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow._remove_existing(symlink)

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

    workflow = InitWorkflow(dpath_root=tmp_path)

    try:
        with pytest.raises(PermissionError):
            workflow._remove_existing(test_dir)
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

    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow._remove_existing(broken_symlink)

    assert not broken_symlink.is_symlink()
    assert not broken_symlink.exists()


def test_is_file(dpath_root: Path):
    dpath_root.touch()

    with pytest.raises(FileExistsError, match="Dataset is an existing file"):
        workflow = InitWorkflow(dpath_root=dpath_root)
        workflow.run()


def test_custom_layout(dpath_root: Path):
    workflow = InitWorkflow(
        dpath_root=dpath_root, fpath_layout=DPATH_LAYOUTS / "layout-0.1.0.json"
    )
    workflow.run()

    # check some of the paths from the old spec exist
    assert (dpath_root / "proc").exists()
    assert (dpath_root / "dicom").exists()


def test_run_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    workflow = InitWorkflow(dpath_root=tmp_path)
    workflow.run_cleanup()
    assert f"Successfully initialized a dataset at {workflow.dpath_root}" in caplog.text


def test_init_bids(tmp_path):
    """Create dummy BIDS dataset to use during init.

    Make sure:
    - manifest is created with the right content
    - all the files are there after init (by default the copy mode is used).
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_copy = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_copy,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )
    workflow = InitWorkflow(dpath_root=dpath_root, bids_source=bids_to_copy)
    workflow.run()

    assert isinstance(workflow.manifest, Manifest)
    assert workflow.manifest[Manifest.col_participant_id].to_list() == ["01", "01"]
    assert workflow.manifest[Manifest.col_visit_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_session_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_datatype].to_list() == [
        ["anat", "func"],
        ["anat", "func"],
    ]

    source_files = [x.relative_to(bids_to_copy) for x in bids_to_copy.glob("**/*")]
    target_files = [
        x.relative_to(dpath_root / "bids") for x in dpath_root.glob("bids/**/*")
    ]

    for f in source_files:
        assert f in target_files

    assert (dpath_root / "bids" / "README.md").exists()


def test_init_bids_move_mode(tmp_path):
    """Create dummy BIDS dataset to use during init and use move mode.

    Make sure:
    - manifest is created with the right content
    - all the files are moved after init and the source is empty.
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_copy = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_copy,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )

    source_files_before_init = [
        x.relative_to(bids_to_copy) for x in bids_to_copy.glob("**/*")
    ]

    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_to_copy, mode="move"
    )
    workflow.run()

    assert isinstance(workflow.manifest, Manifest)
    assert workflow.manifest[Manifest.col_participant_id].to_list() == ["01", "01"]
    assert workflow.manifest[Manifest.col_visit_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_session_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_datatype].to_list() == [
        ["anat", "func"],
        ["anat", "func"],
    ]

    source_files_after_init = [
        x.relative_to(bids_to_copy) for x in bids_to_copy.glob("**/*")
    ]
    target_files = [
        x.relative_to(dpath_root / "bids") for x in dpath_root.glob("bids/**/*")
    ]

    for f in source_files_before_init:
        assert f in target_files

    assert len(source_files_after_init) == 0

    assert (dpath_root / "bids" / "README.md").exists()


def test_init_bids_symlink_mode(tmp_path):
    """Create dummy BIDS dataset to use during init and use move symlink.

    Make sure:
    - manifest is created with the right content
    - all the files are linked after init to the source.
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_link = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_link,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )

    source_files_before_init = [
        x.relative_to(bids_to_link) for x in bids_to_link.glob("**/*")
    ]

    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_to_link, mode="symlink"
    )
    workflow.run()

    assert isinstance(workflow.manifest, Manifest)
    assert workflow.manifest[Manifest.col_participant_id].to_list() == ["01", "01"]
    assert workflow.manifest[Manifest.col_visit_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_session_id].to_list() == ["1", "2"]
    assert workflow.manifest[Manifest.col_datatype].to_list() == [
        ["anat", "func"],
        ["anat", "func"],
    ]

    source_files_after_init = [
        x.relative_to(bids_to_link) for x in bids_to_link.glob("**/*")
    ]

    for f in source_files_before_init:
        assert f in source_files_after_init

    assert (dpath_root / "bids").is_symlink()
    # only the directory is linked, not the files within

    assert (dpath_root / "bids").readlink() == bids_to_link

    assert len(source_files_after_init) == 25
    assert (dpath_root / "bids" / "README.md").exists()


def test_init_bids_symlink_readonly(tmp_path):
    """Create dummy BIDS dataset to use during init and use move symlink.

    The BIDS dataset is read-only on disk w/o a README.
    Make sure:
    - InitWorkflow succeeds while warning no README could be created.
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_link = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_link,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )

    source_files_before_init = [
        x.relative_to(bids_to_link) for x in bids_to_link.glob("**/*")
    ]

    # make the source is read-only
    os.chmod(bids_to_link, 0o555)  # +rx

    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_to_link, mode="symlink"
    )
    workflow.run()

    source_files_after_init = [
        x.relative_to(bids_to_link) for x in bids_to_link.glob("**/*")
    ]

    assert len(source_files_after_init) == len(source_files_before_init)
    assert not (dpath_root / "bids" / "README.md").exists()


def test_init_bids_invalid_mode(tmp_path):
    """Create dummy BIDS dataset and pass an invalid mode.

    Make sure:
    - An error is raised when an invalid mode is used.
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_copy = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_copy,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )

    # mode is invalid, should raise an error
    with pytest.raises(ValueError, match="Invalid mode: something"):
        workflow = InitWorkflow(
            dpath_root=dpath_root, bids_source=bids_to_copy, mode="something"
        )
        workflow.run()


def test_init_bids_dry_run(tmp_path):
    """Copy no file when running in dry mode."""
    dpath_root = tmp_path / "nipoppy"
    bids_to_copy = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_copy,
        subjects=["01"],
        sessions=["1", "2"],
        datatypes=["anat", "func"],
    )
    workflow = InitWorkflow(
        dpath_root=dpath_root, bids_source=bids_to_copy, dry_run=True
    )
    workflow.run()

    assert not dpath_root.exists()


def test_init_bids_warning_no_session(tmp_path, caplog: pytest.LogCaptureFixture):
    """Create dummy BIDS dataset with no session to use during init.

    Make sure:
    - raise a warning if subject has no session.
    - manifest is created with the right content
    - all the files are there after init.
    """
    dpath_root = tmp_path / "nipoppy"
    bids_to_copy = tmp_path / "bids"
    fids.create_fake_bids_dataset(
        output_dir=bids_to_copy,
        subjects=["01"],
        sessions=None,
        datatypes=["anat", "func"],
    )
    workflow = InitWorkflow(dpath_root=dpath_root, bids_source=bids_to_copy)
    workflow.run()
    assert (
        f"Could not find session-level folder(s) for participant sub-01, using session {FAKE_SESSION_ID} in the manifest"
        in caplog.text
    )

    assert isinstance(workflow.manifest, Manifest)
    assert workflow.manifest[Manifest.col_participant_id].to_list() == ["01"]
    assert workflow.manifest[Manifest.col_visit_id].to_list() == [FAKE_SESSION_ID]
    assert workflow.manifest[Manifest.col_session_id].to_list() == [FAKE_SESSION_ID]
    assert workflow.manifest[Manifest.col_datatype].to_list() == [
        ["anat", "func"],
    ]
