import pathlib
import tempfile

from configatron.configatron_loader import ConfigatronLoader
from configatron.backends.toml import TomlBackend


CONFIG_TOML = '''
[sample_config_only_unsecured]
one = "one"
two = "two"
three = "three"
four = "four"
'''


def test_loading(sample_config_only_unsecured):
    with tempfile.TemporaryDirectory() as tempdir_name:
        tempdir = pathlib.Path(tempdir_name)
        config_path = tempdir / 'sample_config_only_unsecured.toml'
        config_path.write_text(CONFIG_TOML)

        backend = TomlBackend(config_path)
        loader = ConfigatronLoader([backend])

        with loader.load():
            assert sample_config_only_unsecured.one == 'one'
            assert sample_config_only_unsecured.two == 'two'
            assert sample_config_only_unsecured.three == 'three'
            assert sample_config_only_unsecured.four == 'four'
