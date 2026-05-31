# Advanced configuration

This guide describes advanced configuration methods.

## Environment variables and `.env` files

Some {term}`CLI` options, such as `--layout`, can be configured via environment variables.
This will be indicated in the usage message when running `nipoppy <SUBCOMMAND> --help`.

It is also possible to set these options using `.env` environment files.
By default, Nipoppy searches the following locations (in order of decreasing priority):
1. {{dpath_root}}`/.env`: project-level
2. `~/.nipoppy/.env`: user-level
3. `/etc/nipoppy/.env`: system-level

The search paths can be overridden by setting the `NIPOPPY_ENV_PATHS` environment variable with paths separated by the platform path separator
(e.g., `export NIPOPPY_ENV_PATHS="[[NIPOPPY_DPATH_ROOT]]/.env:~/.nipoppy/.env:/etc/nipoppy/.env"` for the default paths).
Only the `[[NIPOPPY_DPATH_ROOT]]` substitution is allowed here.

The overall order for determining the value of options is as follows (highest to lowest priority):
1. Command-line options that are explicitly passed when calling the command
2. Environment variables that are already defined at runtime
3. Environment variables loaded from `.env` file(s) (see above)
4. CLI default values
