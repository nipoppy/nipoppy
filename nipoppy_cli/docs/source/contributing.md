# Contributing

Nipoppy is under active development, and we welcome outside contributions!

Please report bugs or start a conversation about potential enhancements/new features by opening a new [GitHub issue](https://github.com/nipoppy/nipoppy/issues/new/choose).

## Developer setup

Fork the [repository](https://github.com/nipoppy/nipoppy) on GitHub, then clone it and **install it with `dev` dependencies**.
(github-install-section)=

```{code-block} console
git clone https://github.com/nipoppy/nipoppy.git
cd nipoppy
pip install -e "nipoppy_cli/.[dev]"
```

Move into that directory and the `nipoppy_cli` subdirectory:

```{code-block} console
cd nipoppy/nipoppy_cli
```

```{note}
The `nipoppy_cli` subdirectory contains the maintained version of the code. The legacy `nipoppy` directory is still available at the top level of the GitHub repository.
```

Set up [`pre-commit`](https://pre-commit.com/) to apply automatic formatting/linting/etc. when making a new commit:
```{code-block} console
$ pre-commit install
```

## Running the test suite

Within the root directory of the repo, run:
```{code-block} console
$ python -m pytest
```

## Building the documentation

Move the the `docs` directory:
```{code-block} console
$ cd docs
```

Run:
```{code-block} console
$ make html
```

Then open the `build/html/index.html` file in a browser.
