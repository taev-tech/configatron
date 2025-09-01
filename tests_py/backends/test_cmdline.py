from unittest.mock import patch

from configatron._backends.cmdline import CmdlineBackend
from configatron.configatron_loader import ConfigatronLoader

CONFIG_ARGV = [
    '__main__',
    '--sample_config_only_unsecured.one=one',
    '--sample_config_only_unsecured.two=two',
    '--sample_config_only_unsecured.three=three',
    '--sample_config_only_unsecured.four=four',
]


@patch('sys.argv', CONFIG_ARGV)
def test_loading(sample_config_only_unsecured):
    backend = CmdlineBackend()
    loader = ConfigatronLoader([backend])

    with loader.load():
        assert sample_config_only_unsecured.one == 'one'
        assert sample_config_only_unsecured.two == 'two'
        assert sample_config_only_unsecured.three == 'three'
        assert sample_config_only_unsecured.four == 'four'
