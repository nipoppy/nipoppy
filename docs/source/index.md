# Welcome to Nipoppy docs!

Nipoppy is a lightweight framework for standardized organization and processing of neuroimaging-clinical datasets. Its goal is to help users adopt the [FAIR](https://www.go-fair.org/fair-principles/) principles and improve the reproducibility of studies.

<img alt="Nipoppy protocol" src="_static/img/nipoppy_protocol.jpg" width=850px>


The framework includes three components:

1. A **protocol** for data curation and processing

2. A **specification** for dataset organization that extends the [Brain Imaging Data Structure (BIDS) standard](https://bids.neuroimaging.io/)

3. A **command-line interface** and **Python package** that provide user-friendly tools for applying the framework.


To get started, see the [Installation instructions](#installation) and/or the [Quickstart guide](#quickstart).

For high-level-vision refer to following:

::::{grid} 3
:::{grid-item-card}  [Why Nipoppy](overview/why_nipoppy)
The motivation behind creating Nipoppy
:::
:::{grid-item-card}  [The use cases](overview/use_cases)
The practical use cases for various users
:::
:::{grid-item-card}  [The principles](overview/principles)
The inspirations and design principles
:::
::::


```{toctree}
---
hidden:
includehidden:
titlesonly:
caption: High-level-view
---
overview/why_nipoppy
overview/use_cases
overview/principles
```

```{toctree}
---
hidden:
includehidden:
titlesonly:
caption: User guide
---
user_guide/index
```

```{toctree}
---
hidden:
includehidden:
titlesonly:
caption: How-to guides
---
how_to_guides/init/index
```

```{toctree}
---
hidden:
includehidden:
titlesonly:
caption: Reference
---
cli_reference/index
autoapi/index
schemas/index
```

```{toctree}
---
hidden:
includehidden:
titlesonly:
caption: Other
---
changelog
contributing
glossary
installation
quickstart
```
