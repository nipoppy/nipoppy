# "How to?" tutorial series

This tutorial series is meant to give you a hands-on experience of the Nipoppy toolbox. Please have Nipoppy installed on your device (see [Installation](../../overview/installation.md)) and have our example dataset ready:

```{code-block} console
$ git clone https://github.com/nipoppy/tutorial-dataset.git
```

or visit the [GitHub repo](https://github.com/nipoppy/tutorial-dataset) and download the data without using `git`. We show in the videos how to!

## 1. nipoppy init

In this tutorial we will cover how to create a new Nipoppy dataset. More concretely, we will
- run the [`nipoppy init`](../../cli_reference/init.rst) command
- discover the directories that follow the Nipoppy specification
- explore the [`nipoppy status`](../../cli_reference/status.rst) command
- modify the content of the [`manifest.tsv`](../../explanations/manifest.md) file according to our dataset
- and run the [`nipoppy track-curation --regenerate`](../../cli_reference/track_curation.rst) command

Duration: 7:43m

<iframe width="560" height="315" src="https://www.youtube.com/embed/POHCcIHEezE?si=HYgD75sE0kwY0wIu" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## 2. nipoppy pipeline

In this tutorial we will cover how to install a pipeline in a Nipoppy dataset. More concretely, we will
- explore the [`nipoppy pipeline`](../../cli_reference/pipeline_install.rst) subcommands
- learn how to share containers
- set pipeline configurations

Duration: 6:31m

<iframe width="560" height="315" src="https://www.youtube.com/embed/5egRvhzQR2g?si=P6FChitCH2qbkTOK" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## 3. nipoppy reorg

In this tutorial we will cover how to reorganize imaging sourcedata. More concretely, we will
- explore the sourcedata directory
- run the [`nipoppy reorg`](../../cli_reference/reorg.rst) command
- and look at the [`curation_status.tsv](../../glossary.md) file

Duration: 6:06m

<iframe width="560" height="315" src="https://www.youtube.com/embed/udA0FxuMJoc?si=miTxSK9MTpbgvWbl" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

```{attention}
More videos on `nipoppy bidsify`, `process`, `track-processing` and `extract` are in the making and will be published soon! Stay tuned for updates!
```
