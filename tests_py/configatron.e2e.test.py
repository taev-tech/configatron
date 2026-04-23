from typing import Protocol

from dcei import ext_dataclass
from dcei import ext_field
from pydantic import TypeAdapter

from configatron import CfgAnalysis
from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.manager import CfgManager
from configatron.prebaked.backends.memory import MemoryBackend
from configatron.prebaked.backends.memory import MemoryBackendKey
from configatron.types import CfgField
from configatron.types import CfgSource
from configatron.types import Secret


class TestConfigatronE2E:

    def test_roundtrip_lib_and_app_separate(self):
        """Using a memory backend to explicitly set a config, we must
        be able to declare, implement, and use config instances, when
        the library implementation is separate from the concrete app
        config definition.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str = ext_field(CfgField(CfgSource('mem', ('BAR_FIELD',)),))
            baz: str

        foo_val = 314
        bar_val = 'val_bar'
        baz_val = 'super_secret_val'
        backend = MemoryBackend({
            MemoryBackendKey('foons', 'foo', 'foo'): foo_val,
            MemoryBackendKey('foons', 'bar', 'BAR_FIELD'): bar_val,
            MemoryBackendKey('foons', 'baz', 'baz'): baz_val})

        mgmt = CfgManager(FakeConfigImplementation, backends={'mem': backend})
        mgmt.load_once_sync()

        # Deliberately switching between both here
        assert (~FakeConfigImplementation).foo == foo_val
        assert (~FakeConfig).bar == bar_val
        assert (~FakeConfig).baz == baz_val

    def test_roundtrip_combined(self):
        """Using a memory backend to explicitly set a config, we must
        be able to declare, implement, and use config instances, when
        the library implementation is combined (ie, the concrete
        implementation is on the same class as the abstract definition).
        """
        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(metaclass=CfgMeta):
            foo: int
            bar: str = ext_field(CfgField(CfgSource('mem', ('BAR_FIELD',)),))
            baz: Secret[str]

        foo_val = 314
        bar_val = 'val_bar'
        baz_val = 'super_secret_val'
        backend = MemoryBackend({
            MemoryBackendKey('foons', 'foo', 'foo'): foo_val,
            MemoryBackendKey('foons', 'bar', 'BAR_FIELD'): bar_val,
            MemoryBackendKey('foons', 'baz', 'baz'): baz_val})

        mgmt = CfgManager(FakeConfigImplementation, backends={'mem': backend})
        mgmt.load_once_sync()

        assert (~FakeConfigImplementation).foo == foo_val
        assert (~FakeConfigImplementation).bar == bar_val
        assert (~FakeConfigImplementation).baz == baz_val


class TestSerializationE2E:

    def test_analysis_roundtrip(self):
        """A roundtrip de/serialization of a config analysis using
        pydantic must complete successfully.
        """
        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(metaclass=CfgMeta):
            foo: int
            bar: str = ext_field(CfgField(CfgSource('mem', ('BAR_FIELD',)),))
            baz: Secret[str]

        mgmt = CfgManager(FakeConfigImplementation, backends={})

        type_adapter = TypeAdapter(CfgAnalysis)
        audit = mgmt.audit_configs()

        serialized = type_adapter.dump_json(audit)
        deserialized = type_adapter.validate_json(serialized)

        assert deserialized == audit
