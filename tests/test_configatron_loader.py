import dataclasses

import pytest

from configatron._runtime_state import _LOADED_CONFIG
from configatron._runtime_state import RawLookupKey
from configatron.configatron_ import configatron
from configatron.configatron_ import secret
from configatron.configatron_ import unsecured
from configatron.configatron_loader import ConfigatronLoader
from configatron.exceptions import ConfigKeyNotFound


@dataclasses.dataclass
class FakeBackend:
    allow_secret: bool
    allow_unsecured: bool

    lookup: dict = dataclasses.field(default_factory=dict)

    def load(self, keyspace):
        return self.lookup

    def add_key(self, namespace, name, value):
        key = RawLookupKey(namespace=namespace, name=name)
        self.lookup[key] = value


class TestConfigatronLoader:

    def test_load_single_backend_complete(self):
        fake_backend = FakeBackend(allow_secret=True, allow_unsecured=True)
        fake_backend.add_key('test', 'test_secret', 'foo')
        fake_backend.add_key('test', 'test_unsecured', 'bar')
        key1 = RawLookupKey('test', 'test_secret')
        key2 = RawLookupKey('test', 'test_unsecured')

        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        loader = ConfigatronLoader([fake_backend])

        with loader.load():
            state = _LOADED_CONFIG.get()
            assert key1 in state.lookup
            assert state.lookup[key1] == 'foo'
            assert key2 in state.lookup
            assert state.lookup[key2] == 'bar'

    def test_load_double_backend_complete(self):
        fake_backend_1 = FakeBackend(allow_secret=True, allow_unsecured=False)
        fake_backend_1.add_key('test', 'test_secret', 'foo')
        key1 = RawLookupKey('test', 'test_secret')
        fake_backend_2 = FakeBackend(allow_secret=False, allow_unsecured=True)
        fake_backend_2.add_key('test', 'test_unsecured', 'bar')
        key2 = RawLookupKey('test', 'test_unsecured')

        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        loader = ConfigatronLoader([fake_backend_1, fake_backend_2])

        with loader.load():
            state = _LOADED_CONFIG.get()
            assert key1 in state.lookup
            assert state.lookup[key1] == 'foo'
            assert key2 in state.lookup
            assert state.lookup[key2] == 'bar'

    def test_load_double_backend_incomplete(self):
        fake_backend_1 = FakeBackend(allow_secret=True, allow_unsecured=False)
        fake_backend_1.add_key('test', 'test_secret', 'foo')
        fake_backend_2 = FakeBackend(allow_secret=False, allow_unsecured=True)
        fake_backend_2.add_key('test', 'test_unsecured', 'bar')

        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()
            test_missing: str = unsecured()

        loader = ConfigatronLoader([fake_backend_1, fake_backend_2])

        with pytest.raises(ConfigKeyNotFound):
            with loader.load():
                pass

    def test_partial_access_in_later_backends(self):
        fake_backend_1 = FakeBackend(allow_secret=True, allow_unsecured=False)
        fake_backend_1.add_key('test', 'test_secret', 'foo')
        key1 = RawLookupKey('test', 'test_secret')
        fake_backend_2 = FakeBackend(allow_secret=False, allow_unsecured=True)
        fake_backend_2.add_key('test', 'test_unsecured', 'bar')
        key2 = RawLookupKey('test', 'test_unsecured')
        assertion_checked = False

        def load_and_assert(keyspace):
            nonlocal assertion_checked
            state = _LOADED_CONFIG.get()
            assert key1 in state.lookup
            assertion_checked = True
            return fake_backend_2.lookup

        fake_backend_2.load = load_and_assert

        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()
            test_missing: str = unsecured()

        loader = ConfigatronLoader([fake_backend_1, fake_backend_2])

        with pytest.raises(ConfigKeyNotFound):
            with loader.load():
                state = _LOADED_CONFIG.get()
                assert key2 in state.lookup
                assert assertion_checked
