# Reorganizing imaging sourcedata

Nipoppy distinguishes between "pre- and post-reorg status" prior to BIDS conversion. Every neuroimaging unit oragnizes the original storage of their sourcedata differently and even within units, sourcedata is often messy in different ways, making it hard to use BIDSification tools directly. Often we find that there is a gap between state of the out-of-scanner vs. ready-for-bidsification data. Nipoppy breaks this process down and provides a unified way to deal with sourcedata which simplifies BIDSification.

## Sourcedata in Nipoppy

The Nipoppy directory tree for the imaging sourcedata looks like the following:

```{code-block}
├── imaging
│   ├── curation_status.tsv
│   ├── downloads
│   ├── pre_reorg
│   ├── post_reorg
│   └── README.md
```

**Example content for the imaging sourcedata directories:**

<html>
<head><style>
table {
	border-collapse:collapse;
}
tr {
	border:none;
}
th, td {
	border-collapse:collapse;
	border: 1px solid black;
	padding-top:0;
	padding-bottom:0;
}
.verticalSplitplusBottomLeft {
    border-top:none;
    border-bottom:1px solid black;
    border-left:none;
}
.verticalSplitplusBottomRight {
    border-top:none;
    border-bottom:1px solid black;
    border-right:none;
}
.verticalSplitplusBottomMiddle {
    border-top:none;
    border-bottom:1px solid black;
}
.verticalSplit {
	border-top:none;
	border-bottom:none;
}
.verticalSplit:first-of-type {
	border-left:none;
}
.verticalSplit:last-of-type {
	border-right:none;
}
</style></head>
<body>
<table>
<tr>
<th class="verticalSplitplusBottomLeft"> <b> <code>downloads </code></b></th> <th class="verticalSplitplusBottomMiddle"> <b><code>pre-reorg</code> </b></th> <th class="verticalSplitplusBottomRight"> <b><code>post-reorg </code></b></th>
</tr>
<tr>
<td class="verticalSplit"> Arbitrarily organized sourcedata downloaded in a compressed or archived file </td> <td class="verticalSplit"> Arbitrarily organized sourcedata in an uncompressed state </td> <td class="verticalSplit"> Organized sourcedata after running <code>nipoppy reorg</code>, ready for BIDSification </td>
</tr>
<tr>
<td class="verticalSplit">

```
├── downloads
│   ├── example.zip
│   └── README.md
```

or

```
├── downloads
│   ├── example.tar
│   └── README.md
```

or

```
├── downloads
│   ├── example.tar.gz
│   └── README.md
```


</td>
<td class="verticalSplit">


```
├── pre_reorg
│   ├── 01
│   │   ├── 1
│   │   │   ├── protocol_1/
│   │   │   │   ├── 001.dcm
│   │   │   │   ├── …
│   │   │   │   └── 084.dcm
│   │   │   ├── protocol_2/
│   │   │   │   ├── 100.dcm
│   │   │   │   ├── …
│   │   │   │   └── 184.dcm
│   ├── 02
│   │   ├── 1
│   │   │   ├── protocol_1/
│   │   │   │   ├── 001.dcm
│   │   │   │   ├── …
│   │   │   │   └── 084.dcm
│   │   │   ├── protocol_2/
│   │   │   │   ├── 100.dcm
│   │   │   │   ├── …
│   │   │   │   └── 184.dcm
│   └── README.md
```


</td>
<td class="verticalSplit">


```
├── post_reorg
│   ├── sub-01
│   │   ├── ses-1
│   │   │   ├── 001.dcm
│   │   │   ├── …
│   │   │   ├── 084.dcm
│   │   │   ├── 100.dcm
│   │   │   ├── …
│   │   │   ├── 184.dcm
│   ├── sub-02
│   │   ├── ses-1
│   │   │   ├── 001.dcm
│   │   │   ├── …
│   │   │   ├── 084.dcm
│   │   │   ├── 100.dcm
│   │   │   ├── …
│   │   │   ├── 184.dcm
│   └── README.md

# flat list of dicom files and
sub- and ses- prefix added
```


</td>
</table>
</body>
</html>

## `nipoppy reorg`

### Requirements for running `nipoppy reorg`

- uncompressed DICOM sourcedata in {{dpath_pre_reorg}}. You can check this by running

```console
$ nipoppy status --dataset <NIPOPPY_PROJECT_ROOT>
```

The output should list the number of participants that are present in both the `manifest.tsv` file and in {{dpath_pre_reorg}} but are not in {{dpath_post_reorg}} yet, according to the {term}`curation status file`. These are the participants and session Nipoppy will loop over when running `nipoppy reorg`.  

- file organization in {{dpath_pre_reorg}} must follow a subject first-session second manner (see next section for help if this is not the case for your data)
- the `manifest.tsv` file must list all participants and sessions
- subject folder and session folder are not allowed to have the BIDS-specific prefixes: subject and session folders need to be named exactly as indicated in the `manifest.tsv` file

If all of these requirements are statisfied, you can run

```console
$ nipoppy reorg --dataset <NIPOPPY_PROJECT_ROOT>
```

For each participant-session pair, Nipoppy
- "copies" (the default is to create symlinks) files from the {{dpath_pre_reorg}} directory to the {{dpath_post_reorg}} directory into a flat list
- adds a `sub-` prefix to all participant folders and a `ses-` prefix to all session folders

You can check the successful reorganization in the {term}`curation status file` or simply by running

```console
$ nipoppy status --dataset <NIPOPPY_PROJECT_ROOT>
```

### Customizing the `nipoppy reorg` behavior

If the file organization in {{dpath_pre_reorg}} does not follow a subject first-session second manner but vice versa, you can simply set `"DICOM_DIR_PARTICIPANT_FIRST"` to `"false"` in the {term}`global configuration file <DICOM_DIR_PARTICIPANT_FIRST>`. 

(dicom-dir-map-example)=
If the raw imaging data are not organized in any of these two structures, a custom tab-separated file can be created to map each unique participant-session pair to a directory path (relative to {{dpath_pre_reorg}}). This path to this mapping file must be specified in the `"DICOM_DIR_MAP_FILE"` in the {term}`global configuration file <DICOM_DIR_MAP_FILE>`. See the {ref}`schema reference <dicom-dir-map-schema>` for more information.

Here is an example file for a dataset that already uses the `ses-` prefix for sessions:

```{csv-table}
---
file: ../../../../nipoppy/data/examples/sample_dicom_dir_map.tsv
header-rows: 1
delim: tab
---
```

````{admonition} Raw content of the example DICOM directory mapping file
---
class: dropdown
---
```{literalinclude} ../../../../nipoppy/data/examples/sample_dicom_dir_map.tsv
---
linenos: True
---
```
````
