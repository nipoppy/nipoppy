"""Snapshot test for sample_global_config.json.

Several docs pages pull this file in with ``literalinclude`` and
``emphasize-lines`` pointing at specific line numbers. When the live file
changes, the highlighted lines can silently drift out of sync. This test
fails on any mismatch so a contributor remembers to update both the
snapshot and the affected docs pages.

Pages currently referencing ``sample_global_config.json`` with
``emphasize-lines``:

- ``docs/source/how_to_guides/parallelization/hpc_scheduler.md``
- ``docs/source/how_to_guides/docker/index.md``
- ``docs/source/tutorials/mriqc_from_bids/index.md``
- ``docs/source/overview/quickstart/index.md``
"""

from pathlib import Path

LIVE_FILE = (
    Path(__file__).parents[2]
    / "nipoppy"
    / "data"
    / "examples"
    / "sample_global_config.json"
)
SNAPSHOT_FILE = Path(__file__).parent / "sample_global_config-snapshot.json"


def test_sample_global_config_matches_snapshot():
    live = LIVE_FILE.read_text()
    snapshot = SNAPSHOT_FILE.read_text()
    assert live == snapshot, (
        f"{LIVE_FILE.name} has changed but the docs snapshot at "
        f"{SNAPSHOT_FILE.relative_to(Path(__file__).parents[2])} hasn't been "
        "updated. Update the snapshot copy and double-check that the "
        "`emphasize-lines` directives in the docs pages still point at the "
        "right lines (and that the surrounding prose still makes sense)."
    )
