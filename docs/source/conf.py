"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import os

from nipoppy._version import __version__
from nipoppy.layout import DEFAULT_LAYOUT_INFO  # for substitutions

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Nipoppy"
copyright = "2024, NeuroDataScience-ORIGAMI Lab"
author = "NeuroDataScience-ORIGAMI Lab"

# The version info for the project you're documenting, acts as replacement
# for |version| and |release|, also used in various other places throughout
# the built documents.
#
# The short X.Y version.
version = __version__

# The full version, including alpha/beta/rc tags.
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autoapi.extension",
    "myst_parser",
    "sphinxarg.ext",
    "sphinx_copybutton",
    "sphinx_github_changelog",
    "sphinx-jsonschema",
    "sphinx_togglebutton",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = [
    # not ideal but otherwise we wrongly get a warning
    "user_guide/inserts/boutiques_stub.md",
]

nitpicky = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

html_css_files = [
    "theme.css",
]

# -- Furo configuration ------------------------------------------------------
#  https://pradyunsg.me/furo/customisation/#customisation

html_css_files = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/fontawesome.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/solid.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/brands.min.css",
]

html_theme_options = {
    "source_repository": "https://github.com/nipoppy/nipoppy",
    "source_branch": "main",
    "source_directory": "docs/source",
    "sidebar_hide_name": True,
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/nipoppy/nipoppy",
            "html": "",
            "class": "fa-brands fa-solid fa-github fa-2x",
        },
        {
            "name": "Discord",
            "url": "https://discord.gg/dQGYADCCMB",
            "html": "",
            "class": "fa-brands fa-solid fa-discord fa-2x",
        },
    ],
}

html_logo = "../../logo/logo_with_name.svg"
html_favicon = "../../logo/logo_square.svg"
html_title = "Nipoppy"

# -- Intersphinx configuration ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "python": ("https://docs.python.org/3", None),
}

# -- MyST configuration -------------------------------------------------------

myst_enable_extensions = ["fieldlist", "substitution"]

myst_heading_anchors = 5

template_strings_bids_runner = [
    "",
    "The default pipeline invocation files (in {{dpath_pipelines}}`/<PIPELINE_NAME>-<PIPELINE_VERSION>`) can be modified by changing existing values or adding new key-value pairs.",
    "",
    "```{tip}",
    "Run the pipeline on a single participant and session with the `--simulate` flag to check/debug custom invocation files.",
    "```",
    "```{note}",
    "To account for invocations needing to be different for different participants and sessions (amongst other things), Nipoppy invocations are actually templates that need to be slightly processed at runtime to replace template strings by actual values. Recognized template strings include:",
    "- `[[NIPOPPY_PARTICIPANT_ID]]`: the participant ID *without* the `sub-` prefix",
    "- `[[NIPOPPY_SESSION_ID]]`: the session ID *without* the `ses-` prefix",
    "- `[[NIPOPPY_BIDS_PARTICIPANT_ID]]`: the participant ID *with* the `sub-` prefix",
    "- `[[NIPOPPY_BIDS_SESSION_ID]]`: the session ID *with* the `ses-` prefix",
    "- `[[NIPOPPY_<LAYOUT_PROPERTY>]]`, where `<LAYOUT_PROPERTY>` is a property in the Nipoppy {ref}`dataset layout configuration file <layout-schema>` (all uppercase): any path defined in the Nipoppy dataset layout",
    "```",
]
template_strings_proc_runner = template_strings_bids_runner[:-1] + [
    f"- `[[NIPOPPY_DPATH_PIPELINE_OUTPUT]]`: the output directory for this pipeline, i.e. `{DEFAULT_LAYOUT_INFO.dpath_derivatives}/<PIPELINE_NAME>/<PIPELINE_VERSION>/output`",
    f"- `[[NIPOPPY_DPATH_PIPELINE_WORK]]`: the working directory for this pipeline run, which will be a subdirectory of `{DEFAULT_LAYOUT_INFO.dpath_derivatives}/<PIPELINE_NAME>/<PIPELINE_VERSION>/work`",
    "- `[[NIPOPPY_DPATH_PIPELINE_BIDS_DB]]`: the [PyBIDS](https://bids-standard.github.io/pybids/) database for the participant and session",
    "```",
]

myst_substitutions = {
    "dpath_root": f"`{DEFAULT_LAYOUT_INFO.dpath_root}`",
    "dpath_downloads": f"`{DEFAULT_LAYOUT_INFO.dpath_downloads}`",
    "dpath_scratch": f"`{DEFAULT_LAYOUT_INFO.dpath_scratch}`",
    "dpath_pre_reorg": f"`{DEFAULT_LAYOUT_INFO.dpath_pre_reorg}`",
    "dpath_post_reorg": f"`{DEFAULT_LAYOUT_INFO.dpath_post_reorg}`",
    "dpath_logs": f"`{DEFAULT_LAYOUT_INFO.dpath_logs}`",
    "dpath_bids": f"`{DEFAULT_LAYOUT_INFO.dpath_bids}`",
    "dpath_pipelines": f"`{DEFAULT_LAYOUT_INFO.dpath_pipelines}`",
    "dpath_pipeline_output": f"`{DEFAULT_LAYOUT_INFO.get_dpath_pipeline_output('<PIPELINE_NAME>', '<PIPELINE_VERSION>')}`",
    "dpath_pipeline_idp": f"`{DEFAULT_LAYOUT_INFO.get_dpath_pipeline_idp('<PIPELINE_NAME>', '<PIPELINE_VERSION>')}`",
    "dpath_pybids_db": f"`{DEFAULT_LAYOUT_INFO.dpath_pybids_db}`",
    "fpath_doughnut": f"`{DEFAULT_LAYOUT_INFO.fpath_doughnut}`",
    "fpath_imaging_bagel": f"`{DEFAULT_LAYOUT_INFO.fpath_imaging_bagel}`",
    "fpath_manifest": f"`{DEFAULT_LAYOUT_INFO.fpath_manifest}`",
    "fpath_config": f"`{DEFAULT_LAYOUT_INFO.fpath_config}`",
    "content_dpath_pre_reorg": (
        "Arbitrarily organized raw imaging data (DICOMs or NIfTIs)"
    ),
    "content_dpath_post_reorg": (
        "Raw imaging data (DICOMs or NIfTIs) organized in a way "
        "that facilitates BIDS conversion"
    ),
    "content_dpath_bids": (
        "Raw imaging data (NIfTIs) organized according to the BIDS standard"
    ),
    "content_dpath_pipeline_output": (
        "Derivative files produced by processing pipelines"
    ),
    "content_dpath_pipeline_idp": (
        "Imaging-derived phenotypes (IDPs) produced by extraction pipelines"
    ),
    "template_strings_bids_runner": "\n".join(template_strings_bids_runner),
    "template_strings_proc_runner": "\n".join(template_strings_proc_runner),
}

# -- Autodoc/AutoAPI configuration ----------------------------------------------------

autodoc_typehints = "description"

autoapi_dirs = ["../../nipoppy"]
autoapi_ignore = ["*_version*", "*/cli/*"]
autoapi_options = [
    "members",
    "undoc-members",
    # "private-members",
    # "show-inheritance",
    # "show-module-summary",
    # "special-members",
    "imported-members",
]
autoapi_member_order = "groupwise"
autoapi_own_page_level = "class"
autoapi_template_dir = "_templates/autoapi"

# ignore some auto doc related warnings
#  see https://github.com/sphinx-doc/sphinx/issues/10785
# suppress_warnings = ["autoapi"]

nitpick_ignore = [
    ("py:class", "Path"),
    ("py:class", "optional"),
    ("py:class", "pd.DataFrame"),
    ("py:class", "bids.BIDSLayout"),
    ("py:class", "argparse.HelpFormatter"),
    ("py:class", "argparse._SubParsersAction"),
    ("py:class", "argparse._ActionsContainer"),
    ("py:class", "StrOrPathLike"),
    ("py:class", "nipoppy.env.StrOrPathLike"),
    ("py:class", "typing_extensions.Self"),
]

# -- Sphinx Github Changelog configuration ------------------------------------

# PAT needs to be set as environment variable in Read the Docs project settings
# fine-grained token permissions:
#   - nipoppy/nipoppy repository
#   - read access to code + metadata
sphinx_github_changelog_token = os.environ.get("NIPOPPY_RELEASES_PAT")

# -- Copybutton configuration -------------------------------------------------
copybutton_exclude = ".linenos, .gp"
copybutton_selector = "div:not(.no-copybutton) > div.highlight > pre"

# -- JSON Schema configuration ------------------------------------------------
jsonschema_options = {
    "lift_definitions": True,
    "auto_reference": True,
    "auto_target": True,
}

# # TODO
# def linkcode_resolve(domain, info):
#     if domain != "py":
#         return None
#     if not info["module"]:
#         return None
#     filename = info["module"].replace(".", "/")
#     return f"https://github.com/""
