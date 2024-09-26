# Contributing

Nipoppy is under active development, and we welcome outside contributions!

Below are some guidelines that could be helpful for potential contributors.

## Contributing through GitHub

Nipoppy development happens on [GitHub](https://github.com/). You will need an account to participate in issue threads and contribute code. Instructions for setting up an account can be found [here](https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github).


## Identifying an issue to work on

The best way to get started contributing is to explore the list of open issues in our [GitHub repository](https://github.com/nipoppy/nipoppy/issues).

When you are ready to contribute, we welcome you to join the conversation through one of these issues, or open a new issue referencing a change you would like to see or contribute. Ensuring that a relevant issue is open before you start contributing code is important because it allows others in the project to discuss your idea and tell you where your contribution would be the most helpful.

- **If the issue you want to work on already exists**: Comment on the open issue to indicate you would like to work on it, along with any clarification/implementation questions you have
    - If someone is already [assigned to the issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/assigning-issues-and-pull-requests-to-other-github-users), the task is actively being worked on and a solution will soon be proposed. Feel free to share some helpful resources or pointers that may be interesting to the person who is working the issue, and/or check back in a couple of days.

- **If the issue you want to work on does not exist**: Open a new issue describing your proposed change and why it is necessary/beneficial. The more detail here, the better!
    - This allows members of the Nipoppy developer team to confirm that you will not be overlapping with currently active work and that everyone is on the same page about the task to be accomplished.

If you would like to contribute but are not sure where to start, we recommend looking for open issues with the following labels:

- ![good first issue](https://img.shields.io/github/labels/nipoppy/nipoppy/good%20first%20issue) *Issue that is good for a new or beginner contributor, as it does not involve a steep learning curve or advanced understanding of the codebase. (Please note: if you're a seasoned contributor, we would appreciate if you could select a different issue to work on to keep these available for less experienced folks!)*

<!-- ![PR welcome](https://img.shields.io/github/labels/neurobagel/planning/PR%20welcome)
*Issue that is not an internal priority, but external pull requests to address it are welcome.*

![quick fix](https://img.shields.io/github/labels/neurobagel/planning/quick%20fix):
*Issue that should involve minimal planning or implementation work, given an understanding of the relevant code.* -->

## Developer environment setup

```{tip}
You should use a Python environment dedicated to Nipoppy development (see [here](#python-env-instructions) for instructions).
```

First, [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) the [repository](https://github.com/nipoppy/nipoppy) on GitHub.

Then, in a Terminal window, clone the repository and **install it with `dev` dependencies**:
```{code-block} console
$ git clone https://github.com/nipoppy/nipoppy.git
$ cd nipoppy
$ pip install -e ".[dev]"
```

Set up [`pre-commit`](https://pre-commit.com/) to apply automatic formatting/linting/etc. when making a new commit:
```{code-block} console
$ pre-commit install
```

It is a good idea to create a new branch when you start working on a new issue. Branches can be created [through GitHub](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-and-deleting-branches-within-your-repository) or with the `git` command-line in the Terminal.

To keep up with changes in the Nipoppy repository while you work and avoid merge conflicts later on, make sure to:
- [Add the "upstream" Nipoppy repository as a remote](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#configuring-git-to-sync-your-fork-with-the-upstream-repository) to your locally cloned repository
- [Keep your fork up to date](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork#syncing-a-fork-branch-from-the-command-line) with the upstream repository

## Pull requests

All changes to the `main` branch of the code repository need to be done through GitHub [pull requests (PRs)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

Nipoppy PR reviews may use the following emoji signifiers:
- 🧑‍🍳: Ready to merge or approved without suggestions
- 🍒: Some optional/suggested changes that could be nice to have but are not required to merge

If (required) changes are requested, please re-request a review from the reviewer once the comments have been addressed.

## Running the test suite locally

Whenever a pull request is created or updated, the entire test suite is run for all supported Python versions. The test suite can also be run locally by navigating to the root directory of the repo and running:
```{code-block} console
$ pytest
```

This will run the entire test suite, but it is also possible to only run a subset of tests. See the [pytest documentation](https://docs.pytest.org/en/latest/how-to/usage.html) for more information.

## Building the documentation

We use the [Sphinx framework](https://www.sphinx-doc.org/en/master/) for our documentation.To build the documentation locally, move the the `docs` directory:
```{code-block} console
$ cd docs
```

Then run:
```{code-block} console
$ make html
```

Then open the `build/html/index.html` file in a browser.

## Making a release

Inside the repository, run:
```{code-block} console
$ git tag <NEW_VERSION>
$ git push upstream tag <NEW_VERSION>
```

This assumes that the Git repository has a remote called `upstream` that is pointing to https://github.com/nipoppy/nipoppy.git.
