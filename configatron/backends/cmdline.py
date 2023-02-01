import sys


class CmdlineBackend:
    """A config backend that uses sys.argv (ie, the command line) for
    storage. Note that this is intended purely as an ad-hoc override to
    other config options, and not as a primary way to specify config
    variables. As such, it does **not** automatically populate help
    text with possible values. If you want that, you'll need to build
    it yourself.

    Values are only supported as keywords, and only of the pattern
    --namespace.foo=bar. Anything else will be ignored by the backend.

    Empty values are supported -- ex,
    ``--namespace.foo= --namespace.bar=baz`` will be interpreted to mean
    that namespace.foo is the empty string. Again, this is meant as a
    quick and dirty override, so we're emphasizing utility over
    cleanliness.
    """

    allow_secret = False
    allow_unsecured = True

    def load(self, keyspace):
        expected_keys = {}

        for key in keyspace:
            arg_prefix = f'--{key.namespace}.{key.name}'
            expected_keys[arg_prefix] = key

        found_values = {}
        for argv_value in sys.argv[1:]:
            argv_value_split = argv_value.split('=', maxsplit=1)

            if len(argv_value_split) == 2:  # noqa: PLR2004
                maybe_argv_prefix, maybe_config_value = argv_value_split

                if maybe_argv_prefix in expected_keys:
                    found_values[expected_keys[maybe_argv_prefix]] = (
                        maybe_config_value)

        return found_values
