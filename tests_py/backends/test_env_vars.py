import os
from unittest.mock import patch

from configatron._backends.env_vars import EnvVarBackend
from configatron.configatron_loader import ConfigatronLoader

CONFIG_ENVIRON = {
    'SAMPLE_CONFIG_ONE': 'one',
    'SAMPLE_CONFIG_TWO': 'two',
    'SAMPLE_CONFIG_THREE': 'three',
    'SAMPLE_CONFIG_FOUR': 'four',
}


@patch.dict(os.environ, CONFIG_ENVIRON, clear=True)
def test_loading(sample_config):
    backend = EnvVarBackend()
    loader = ConfigatronLoader([backend])

    with loader.load():
        assert sample_config.one == 'one'
        assert sample_config.two == 'two'
        assert sample_config.three == 'three'
        assert sample_config.four == 'four'
