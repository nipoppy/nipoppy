# Configuring projects

This guide describes advanced configuration methods.

## Environment variables and `.env` files

Some {term}`CLI` options, such as `--layout`, can be configured via environment variables.
This will be indicated in the usage message when running `nipoppy <SUBCOMMAND> --help`.

It is also possible to set these options using `.env` environment files.
By default, Nipoppy searches the following locations (in order of decreasing priority):
- {{dpath_root}}`/.env`: project-level
- `~/.nipoppy/.env`: user-level
- `/etc/nipoppy/.env`: system-level

Content from these files has lower priority compared to already-defined environment variables, which themselves can be overridden by explicitly passing CLI options.

The search paths can be overridden by setting the `NIPOPPY_ENV_PATHS` environment variable with paths separated by the platform path separator
(e.g., `export NIPOPPY_ENV_PATHS="[[NIPOPPY_DPATH_ROOT]]/.env:~/.nipoppy/.env:/etc/nipoppy/.env` for the default paths).
