# Configatron

General-purpose configuration based on annotations. Uses TOML files for plaintext config, and pluggable modules for secrets (for example, AWS secrets manager).

## A note on inheritance

+   If you really want config inheritance, you should hard code it as an additional backend. So for example, if you wanted to have a default local config with an additional per-developer local config (and add the latter to your gitignore), the way you'd do that is that whatever if block decides which file to use for which environment, also adds a second backend in the local environment for the dev-specific override file

## Questions that I need to answer and document:

+   what are allowed values for namespaces?
+   same question, but for key names
+   does the cmdline backend support quoting for values?
