import os
from collections.abc import Mapping
from collections.abc import Sequence
from unittest.mock import Mock
from unittest.mock import patch

from configatron.backends import KeyspaceSummary
from configatron.cfg_abstract import CfgMeta
from configatron.prebaked.backends.env_vars import EnvVarBackend
from configatron.types import CfgFieldDesc
from configatron.types import CfgSource

CONFIG_ENVIRON = {
    'SAMPLE_CONFIG_ONE': 'one',
    'SAMPLE_CONFIG_TWO': 'two',
    'SAMPLE_CONFIG_THREE': 'three',
    'SAMPLE_CONFIG_SPECIAL': 'four',
}
_FAKE_CFG_CLS = Mock(CfgMeta)
DESC_1 = CfgFieldDesc(_FAKE_CFG_CLS, 'sample_config', 'one')
DESC_2 = CfgFieldDesc(_FAKE_CFG_CLS, 'sample_config', 'two')
DESC_3 = CfgFieldDesc(_FAKE_CFG_CLS, 'sample_config', 'three')
DESC_4 = CfgFieldDesc(_FAKE_CFG_CLS, 'sample_config', 'four')


@patch.dict(os.environ, CONFIG_ENVIRON, clear=True)
class TestEnvVarBackend:

    def test_loading(self):
        class FakeConfig(metaclass=CfgMeta):
            ...

        backend = EnvVarBackend()

        keyspace_info: Mapping[
            str | None, Sequence[tuple[CfgFieldDesc, CfgSource]]
        ] = {
            'sample_config': [
                (DESC_1, CfgSource('backend_foo', ['one'])),
                (DESC_2, CfgSource('backend_foo', ['two'])),
                (DESC_3, CfgSource('backend_foo', ['three'])),
                (DESC_4, CfgSource('backend_foo', ['special'])),
            ]
        }
        keyspace = KeyspaceSummary(keyspace_info)

        retval = backend.load_sync(keyspace, keyspace)

        assert retval[DESC_1] == 'one'
        assert retval[DESC_2] == 'two'
        assert retval[DESC_3] == 'three'
        assert retval[DESC_4] == 'four'
