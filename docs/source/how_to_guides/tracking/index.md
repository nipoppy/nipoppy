# Tracking pipeline statuses

This guide shows how to track the completion status of [BIDSification](#bidsification-pipelines) and [processing](#processing-pipelines) pipelines.

## BIDSification pipelines

The [`nipoppy track-curation`](../../cli_reference/track_curation.rst) command can be used to track dataset curation stages (reorganization and BIDSification).
The command to create a curation status file from scratch is:

```console
$ nipoppy track-curation --regenerate
```

```{note}
Without the `--regenerate` flag, `nipoppy track-curation` will only update the curation status for new participants in the manifest.
```

The above command creates or updates the curation status file at {{fpath_curation_status}}.
A summary of curation statuses can be displayed by running the [`nipoppy status`](../../cli_reference/status.rst) command, which outputs something like this:

```
      Participant counts by session at each Nipoppy checkpoint
             ╷             ╷              ╷               ╷
  session_id │ in_manifest │ in_pre_reorg │ in_post_reorg │ in_bids
 ════════════╪═════════════╪══════════════╪═══════════════╪═════════
      1      │      2      │      0       │       0       │    0
      2      │      2      │      0       │       0       │    0
             ╵             ╵              ╵               ╵
```

```{note}
The `in_pre_reorg` and `in_post_reorg` columns will be collapsed if all participants in the manifest have been BIDSified.
```

Columns related to the curation stages are:

| Name | Description |
|---|---|
| `in_pre_reorg` | Number of participants with data in {{dpath_pre_reorg}} |
| `in_post_reorg` | Number of participants with data in {{dpath_post_reorg}} `/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` |
| `in_bids` | Number of participants with data in {{dpath_bids}} `/sub-<PARTICIPANT_ID>/ses-<SESSION_ID>` |

<!-- TODO add tip box pointing to guide on reorg -->

## Processing pipelines

The [`nipoppy track-processing`](../../cli_reference/track_processing.rst) command can be used to track the completion status of processing pipelines. The minimal command is:

```console
$ nipoppy track-processing --pipeline <PIPELINE_NAME>
```

```{note}
The pipeline version and step name can be optionally specified using the `--pipeline-version` and `--pipeline-step` arguments respectively. By default, the latest version and the first step are used.

It is also possible to restrict the run to a single participant and/or session by using the `--participant-id` and `--session-id` arguments respectively.
```

The above command creates or updates the processing status file at {{fpath_processing_status}}.
A summary of pipeline statuses can be displayed by running the [`nipoppy status`](../../cli_reference/status.rst) command:

```
 Participant counts by session at each Nipoppy
                   checkpoint
             ╷             ╷         ╷
             │             │         │  mriqc
             │             │         │ 23.1.0
  session_id │ in_manifest │ in_bids │ default
 ════════════╪═════════════╪═════════╪═════════
      1      │      2      │    2    │    2
      2      │      2      │    2    │    2
             ╵             ╵         ╵
```

```{tip}
The processing status file can also be uploaded to [https://digest.neurobagel.org](https://digest.neurobagel.org) for filtering and interactive visualizations.
```

### Configuring a pipeline tracker

Pipeline completion criteria are defined through the tracker configuration file.
The name of the tracker configuration file can be found in the pipeline's config file at {{fpath_processing_pipeline_config}}; by default it is called `tracker.json`:

```{literalinclude} ./mriqc_config.json
---
lines: 17-24
emphasize-lines: 6
language: json
---
```

Importantly, pipeline completion status is **not** inferred from exit codes, as trackers are run independently of the pipeline runners.
Instead, the status is determined by checking for the presence of expected output files.

Here is example of tracker configuration file for the MRIQC pipeline, version 23.1.0:
```{literalinclude} ./mriqc-23.1.0-tracker_config.json
```

```{tip}
- The paths are expected to be relative to the {{dpath_pipeline_output}} directory.
- "Glob" expressions (i.e., that include `*`) are allowed in paths. If at least one file matches the expression, then the file will be considered found for that expression.
```

```{note}
The template strings `[[NIPOPPY_<ATTRIBUTE_NAME>]]` are replaced at runtime by appropriate values.
Available template strings are:
- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix",
- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix",
- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix",
- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix",
```

Given a dataset with the following content in {{dpath_pipeline_output}}:
```{literalinclude} ./mriqc_outputs.txt
---
class: no-copybutton
---
```

Running the tracker with the above configuration will result in the processing status file showing:
```{csv-table}
---
file: ./mriqc_processing_status.tsv
header-rows: 1
delim: tab
---
```

```{note}
If there is an existing processing status file, the rows relevant to the specific pipeline, participants, and sessions will be updated. Other rows will be left as-is.
```

The `pipeline_complete` column can have the following values:
* `SUCCESS`: all specified paths have been found
* `FAIL`: at least one of the paths has not been found
