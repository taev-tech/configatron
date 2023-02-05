# Configatron

General-purpose configuration based on annotations. Uses TOML files for plaintext config, and pluggable modules for secrets (for example, AWS secrets manager).

## A note on inheritance

+   If you really want config inheritance, you should hard code it as an additional backend. So for example, if you wanted to have a default local config with an additional per-developer local config (and add the latter to your gitignore), the way you'd do that is that whatever if block decides which file to use for which environment, also adds a second backend in the local environment for the dev-specific override file

## Important TODOs before general use

+   Need to support an explicit set/subset of configs. currently the configs
    are purely based on import-based discovery. but you might have situations
    where you've imported more than you actually want to use, and you want to
    limit which configs to check. this should probably be done within the
    config_loader.load() call, NOT within the loader init

## Questions that I need to answer and document:

+   what are allowed values for namespaces?
+   same question, but for key names
+   does the cmdline backend support quoting for values?
+   should you also support AWS parameter store?

## Backend notes

### Keyring:

+   currently only tested on windows; need to test on osx
