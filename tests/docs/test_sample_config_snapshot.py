"""Guardrail against drift between sample_global_config.json and the docs snapshot."""

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
SOURCE = REPO_ROOT / "nipoppy" / "data" / "examples" / "sample_global_config.json"
SNAPSHOT = Path(__file__).parent / "sample_global_config.snapshot.json"


def test_sample_global_config_snapshot_matches():
    assert SOURCE.read_text() == SNAPSHOT.read_text(), (
        f"{SOURCE.relative_to(REPO_ROOT)} has changed since the docs snapshot was "
        f"taken. Make sure the copy at {SNAPSHOT.relative_to(REPO_ROOT)} is up to "
        "date and check that the highlighted lines in the docs (and the docs "
        "generally) still make sense."
    )
