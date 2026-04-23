from typing import Protocol
from unittest.mock import patch

import pytest
from dcei import ext_dataclass
from dcei import ext_field

from configatron._analysis import FieldAnalysis
from configatron.backends import KeyspaceSummary
from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.manager import CfgManager
from configatron.manager import _CfgFieldRoute
from configatron.manager import _CfgFieldRouteKey
from configatron.manager import _DefiniteCfgSource
from configatron.prebaked.backends.memory import MemoryBackend
from configatron.types import CfgField
from configatron.types import CfgFieldDesc
from configatron.types import CfgSource
from configatron.types import Secret


class NosecretMemoryBackend(MemoryBackend):
    ALLOW_SECRET = False


def _mock_analyze(self):
    """Just make sure that we set an analysis value as needed when
    we're mocking out the analysis method.
    """
    self._analysis = {}


def _mock_build_routes(self):
    """Just make sure that we set a field routes value as needed when
    we're mocking out the build_routes method.
    """
    self._field_routes = {}
    self._keyspaces_by_backend = {}


class TestAnalyzeCfgCls:

    @patch.object(
        CfgManager, '_analyze_configs',
        autospec=True, side_effect=_mock_analyze)
    @patch.object(
        CfgManager, '_build_routes',
        autospec=True, side_effect=_mock_build_routes)
    def test_init_etc(self, analyze_patch, build_routes_patch):
        """Instance __init__ must correctly convert the config classes
        into a dict and store it on the instance. It must also prepare
        the other attributes and all into ``_analyze_configs`` and
        ``_build_routes``.

        Furthermore, the class must intercept attempts to change the
        protected attributes after they've been set.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: str

        backend = MemoryBackend()

        mgmt = CfgManager(FakeConfigImplementation, backends={'mem': backend})
        assert analyze_patch.call_count == 1
        assert build_routes_patch.call_count == 1

        assert len(mgmt.cfg_classes) == 1
        assert mgmt.cfg_classes['foo'] is FakeConfigImplementation
        assert mgmt.backends['mem'] is backend

        with pytest.raises(AttributeError):
            mgmt.cfg_classes = {}

        with pytest.raises(AttributeError):
            mgmt.backends = {}

    @patch.object(CfgManager, '_analyze_configs', autospec=True)
    def test_build_routes_implicit(self, analyze_patch):
        """Building routes, when called without any explicit routes
        defined on fields, must result in the default backend receiving
        the default search keys (the fieldnames).

        For this test, don't worry about filtering based on support for
        secrets.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: str

        backend = MemoryBackend()

        def mock_analyze(cfg_manager):
            cfg_manager._analysis = {
                'foons': (
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'foo'),
                        None,
                        False,
                        False,
                        (CfgSource(None, ('foo',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'bar'),
                        None,
                        False,
                        False,
                        (CfgSource(None, ('bar',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'baz'),
                        None,
                        True,
                        False,
                        (CfgSource(None, ('baz',)),),),)}

        analyze_patch.side_effect = mock_analyze
        mgmt = CfgManager(FakeConfigImplementation, backends={'mem': backend})
        assert analyze_patch.call_count == 1

        assert len(mgmt._field_routes) == 3
        assert len(mgmt._keyspaces_by_backend) == 1

        assert mgmt._field_routes == {
            _CfgFieldRouteKey('foons', 'foo'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'foo'),
                [_DefiniteCfgSource('mem', ('foo',))]),
            _CfgFieldRouteKey('foons', 'bar'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'bar'),
                [_DefiniteCfgSource('mem', ('bar',))]),
            _CfgFieldRouteKey('foons', 'baz'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'baz'),
                [_DefiniteCfgSource('mem', ('baz',))]),
        }
        assert mgmt._keyspaces_by_backend['mem'] == KeyspaceSummary(
            {
                'foons': (
                    # Note that the source backend -> none here is expected,
                    # since they were implicit. The reference to 'mem' is
                    # recovered in the key used in the _keyspaces_by_backend
                    # mapping.
                    (
                        CfgFieldDesc('foons', 'foo'),
                        CfgSource(None, ('foo',))),
                    (
                        CfgFieldDesc('foons', 'bar'),
                        CfgSource(None, ('bar',))),
                    (
                        CfgFieldDesc('foons', 'baz'),
                        CfgSource(None, ('baz',))),)
            })

    @patch.object(CfgManager, '_analyze_configs', autospec=True)
    def test_build_routes_implicit_secrets(self, analyze_patch):
        """Building routes, when called without any explicit routes
        defined on fields, must result in the default backend receiving
        the default search keys (the fieldnames).

        Additionally, backends that don't support secrets must not be
        given routings for secret fields.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: str

        backend = MemoryBackend()

        def mock_analyze(cfg_manager):
            cfg_manager._analysis = {
                'foons': (
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'foo'),
                        None,
                        False,
                        False,
                        (CfgSource(None, ('foo',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'bar'),
                        None,
                        False,
                        False,
                        (CfgSource(None, ('bar',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'baz'),
                        None,
                        True,
                        False,
                        (CfgSource(None, ('baz',)),),),)}

        analyze_patch.side_effect = mock_analyze
        mgmt = CfgManager(FakeConfigImplementation, backends={
            'mem': backend,
            'mem_plaintext': NosecretMemoryBackend()})
        assert analyze_patch.call_count == 1

        assert len(mgmt._field_routes) == 3
        assert len(mgmt._keyspaces_by_backend) == 2

        assert mgmt._field_routes == {
            _CfgFieldRouteKey('foons', 'foo'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'foo'),
                [
                    _DefiniteCfgSource('mem', ('foo',)),
                    _DefiniteCfgSource('mem_plaintext', ('foo',))]),
            _CfgFieldRouteKey('foons', 'bar'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'bar'),
                [
                    _DefiniteCfgSource('mem', ('bar',)),
                    _DefiniteCfgSource('mem_plaintext', ('bar',))]),
            _CfgFieldRouteKey('foons', 'baz'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'baz'),
                [_DefiniteCfgSource('mem', ('baz',))]),
        }
        assert mgmt._keyspaces_by_backend['mem_plaintext'] == KeyspaceSummary(
            {
                'foons': (
                    # Note that the source backend -> none here is expected,
                    # since they were implicit. The reference to 'mem' is
                    # recovered in the key used in the _keyspaces_by_backend
                    # mapping.
                    (
                        CfgFieldDesc('foons', 'foo'),
                        CfgSource(None, ('foo',))),
                    (
                        CfgFieldDesc('foons', 'bar'),
                        CfgSource(None, ('bar',))),)
            })

    @patch.object(CfgManager, '_analyze_configs', autospec=True)
    def test_build_routes_implicit_explicit(self, analyze_patch):
        """A mix of implicit and explicit field routings must be
        correctly routed, and must also apply correct filtering for
        secrets and plaintext config values.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            oof: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foons'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int = ext_field(CfgField(CfgSource('mem', ('FOO_FIELD',)),))
            oof: int = ext_field(CfgField(CfgSource(None, ('OOF_FIELD',)),))
            bar: str = ext_field(CfgField(
                CfgSource('mem_plaintext', ('BAR_FIELD',)),
                CfgSource(None, ('BAR_FIELD_2',)),))
            baz: str

        backend = MemoryBackend()

        def mock_analyze(cfg_manager):
            cfg_manager._analysis = {
                'foons': (
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'foo'),
                        None,
                        False,
                        False,
                        (CfgSource('mem', ('FOO_FIELD',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'oof'),
                        None,
                        False,
                        False,
                        (CfgSource(None, ('OOF_FIELD',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'bar'),
                        None,
                        False,
                        False,
                        (
                            CfgSource('mem_plaintext', ('BAR_FIELD',)),
                            CfgSource(None, ('BAR_FIELD_2',)),),),
                    FieldAnalysis(
                        CfgFieldDesc('foons', 'baz'),
                        None,
                        True,
                        False,
                        (CfgSource(None, ('baz',)),),),)}

        analyze_patch.side_effect = mock_analyze
        mgmt = CfgManager(FakeConfigImplementation, backends={
            'mem': backend,
            'mem_plaintext': NosecretMemoryBackend()})
        assert analyze_patch.call_count == 1

        assert len(mgmt._field_routes) == 4
        assert len(mgmt._keyspaces_by_backend) == 2

        assert mgmt._field_routes == {
            _CfgFieldRouteKey('foons', 'foo'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'foo'),
                [
                    _DefiniteCfgSource('mem', ('FOO_FIELD',)),]),
            _CfgFieldRouteKey('foons', 'oof'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'oof'),
                [
                    _DefiniteCfgSource('mem', ('OOF_FIELD',)),
                    _DefiniteCfgSource('mem_plaintext', ('OOF_FIELD',))]),
            _CfgFieldRouteKey('foons', 'bar'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'bar'),
                [
                    _DefiniteCfgSource('mem_plaintext', ('BAR_FIELD',)),
                    _DefiniteCfgSource('mem', ('BAR_FIELD_2',)),]),
            _CfgFieldRouteKey('foons', 'baz'): _CfgFieldRoute(
                CfgFieldDesc('foons', 'baz'),
                [_DefiniteCfgSource('mem', ('baz',))]),
        }
        assert mgmt._keyspaces_by_backend['mem'] == KeyspaceSummary(
            {
                'foons': (
                    # Note that the source backend -> none here is expected,
                    # since they were implicit. The reference to 'mem' is
                    # recovered in the key used in the _keyspaces_by_backend
                    # mapping.
                    (
                        CfgFieldDesc('foons', 'foo'),
                        CfgSource('mem', ('FOO_FIELD',))),
                    (
                        CfgFieldDesc('foons', 'oof'),
                        CfgSource(None, ('OOF_FIELD',))),
                    (
                        CfgFieldDesc('foons', 'bar'),
                        CfgSource(None, ('BAR_FIELD_2',))),
                    (
                        CfgFieldDesc('foons', 'baz'),
                        CfgSource(None, ('baz',))),)
            })
        assert mgmt._keyspaces_by_backend['mem_plaintext'] == KeyspaceSummary(
            {
                'foons': (
                    # Note that the source backend -> none here is expected,
                    # since they were implicit. The reference to 'mem' is
                    # recovered in the key used in the _keyspaces_by_backend
                    # mapping.
                    (
                        CfgFieldDesc('foons', 'oof'),
                        CfgSource(None, ('OOF_FIELD',))),
                    (
                        CfgFieldDesc('foons', 'bar'),
                        CfgSource('mem_plaintext', ('BAR_FIELD',))),)
            })
