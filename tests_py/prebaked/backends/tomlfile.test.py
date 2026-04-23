from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch

from configatron.backends import KeyspaceSummary
from configatron.cfg_abstract import CfgMeta
from configatron.prebaked.backends.tomlfile import TomlFileBackend
from configatron.types import CfgFieldDesc
from configatron.types import CfgSource

CONFIG_TOML = '''
one = "one"

[sample_config]
two = "two"
three = "three"
special = "four"
'''
DESC_1 = CfgFieldDesc(None, 'one')
DESC_2 = CfgFieldDesc('sample_config', 'two')
DESC_3 = CfgFieldDesc('sample_config', 'three')
DESC_4 = CfgFieldDesc('sample_config', 'four')


@patch.object(Path, 'read_text', autospec=True, return_value=CONFIG_TOML)
class TestTomlFileBackend:

    def test_loading(self, path_patch):
        class FakeConfig(metaclass=CfgMeta):
            ...

        backend = TomlFileBackend('foo.toml')

        keyspace_info: Mapping[
            str | None, Sequence[tuple[CfgFieldDesc, CfgSource]]
        ] = {
            'sample_config': [
                (DESC_2, CfgSource('backend_foo', ('two',))),
                (DESC_3, CfgSource('backend_foo', ('three',))),
                (DESC_4, CfgSource('backend_foo', ('special',))),
            ],
            None: [
                (DESC_1, CfgSource('backend_foo', ('one',))),
            ],
        }
        keyspace = KeyspaceSummary(keyspace_info)

        retval = backend.load_sync(keyspace, keyspace)

        assert path_patch.call_count == 1
        assert retval[DESC_1] == 'one'
        assert retval[DESC_2] == 'two'
        assert retval[DESC_3] == 'three'
        assert retval[DESC_4] == 'four'
