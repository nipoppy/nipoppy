"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Nipoppy"
copyright = "2024, NeuroDataScience-ORIGAMI Lab"
author = "NeuroDataScience-ORIGAMI Lab"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autodoc2",
    "myst_parser",
    "sphinxarg.ext",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

# -- Intersphinx configuration ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "python": ("https://docs.python.org/3", None),
}

# -- MyST configuration -------------------------------------------------------

myst_enable_extensions = ["fieldlist"]

# -- Autodoc2 configuration --------------------------------------------

autodoc2_packages = [
    "../../nipoppy",
]
autodoc2_hidden_objects = [
    "private",
    "inherited",
]
autodoc2_index_template = (
    "Python interface\n"
    "================\n"
    "\n"
    "This page contains auto-generated API reference documentation [#f1]_.\n"
    "\n"
    ".. toctree::\n"
    "   :titlesonly:\n"
    "{% for package in top_level %}\n"
    "   {{ package }}\n"
    "{%- endfor %}\n"
    "\n"
    ".. [#f1] Created with `sphinx-autodoc2 "
    "<https://github.com/chrisjsewell/sphinx-autodoc2>`_\n"
    "\n"
)
autodoc2_docstring_parser_regexes = [
    # this will render all docstrings as Markdown
    (r".*", "myst"),
]
autodoc2_sort_names = True

# # TODO
# def linkcode_resolve(domain, info):
#     if domain != "py":
#         return None
#     if not info["module"]:
#         return None
#     filename = info["module"].replace(".", "/")
#     return f"https://github.com/""
