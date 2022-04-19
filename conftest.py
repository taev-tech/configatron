from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def clean_configatron_registry():
    with patch('configatron._runtime_state.ALL_CONFIGATRONS', {}):
        yield
