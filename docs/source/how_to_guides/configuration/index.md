# Advanced configuration

This guide describes advanced configuration methods.

## Environment variables and `.env` files

Some {term}`CLI` options, such as `--layout`, can be configured via environment variables.
This will be indicated in the usage message when running `nipoppy <SUBCOMMAND> --help`.

It is also possible to set these options using `.env` environment files.
Nipoppy searches the following locations (in order of decreasing priority):
1. {{dpath_root}}`/.nipoppy/.env`: project-level
2. `~/.nipoppy/.env`: user-level

The overall order for determining the value of options is as follows (highest to lowest priority):
1. Command-line options that are explicitly passed when calling the command
2. Environment variables that are already defined at runtime
3. Environment variables loaded from `.env` file(s) (see above)
4. CLI default values
