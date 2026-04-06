from typing import Protocol

import pytest
from dcei import ext_dataclass
from dcei import ext_field

from configatron._analysis import FieldAnalysis
from configatron._analysis import analyze_cfg_cls
from configatron._registry import NormalizedCfgCls
from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.types import CfgField
from configatron.types import CfgSource
from configatron.types import Secret


class TestAnalyzeCfgCls:

    def test_simple_configs(self):
        """A simple config with both secret- and non-secret fields but
        no further customization must return one correct
        ``FieldAnalysis`` per field.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: Secret[str]

        norm_cfg_cls = NormalizedCfgCls(
            abstract_cls=FakeConfig,
            concrete_cls=FakeConfigImplementation)
        retval = analyze_cfg_cls('foo', norm_cfg_cls)

        assert all(
            isinstance(field_analysis, FieldAnalysis)
            for field_analysis in retval)
        assert len(retval) == 3
        assert all(
            not field_analysis.is_concrete_only
            for field_analysis in retval)
        assert all(
            field_analysis.refresh_after_max is None
            for field_analysis in retval)

        by_name = {
            field_analysis.field_desc.name: field_analysis
            for field_analysis in retval}
        assert not by_name['foo'].is_secret
        assert not by_name['bar'].is_secret
        assert by_name['baz'].is_secret
        assert by_name['foo'].sources == (
            CfgSource(backend=None, lookup_keys=('foo',)),)
        assert by_name['bar'].sources == (
            CfgSource(backend=None, lookup_keys=('bar',)),)
        assert by_name['baz'].sources == (
            CfgSource(backend=None, lookup_keys=('baz',)),)

    def test_omitted_implementation_secrecy(self):
        """Config fields that are only declared as secret in the
        abstract class must nonetheless be analyzed as secret.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            # Note: the lack of Secret[...] here is the part we're testing
            baz: str

        norm_cfg_cls = NormalizedCfgCls(
            abstract_cls=FakeConfig,
            concrete_cls=FakeConfigImplementation)
        retval = analyze_cfg_cls('foo', norm_cfg_cls)

        by_name = {
            field_analysis.field_desc.name: field_analysis
            for field_analysis in retval}
        assert not by_name['foo'].is_secret
        assert not by_name['bar'].is_secret
        assert by_name['baz'].is_secret

    def test_implementation_only_field(self):
        """Config fields that are only declared on the concrete
        implementation class must nonetheless be detected (and flagged
        as such).
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

            impl_foo: int
            impl_bar: Secret[str]

        norm_cfg_cls = NormalizedCfgCls(
            abstract_cls=FakeConfig,
            concrete_cls=FakeConfigImplementation)
        retval = analyze_cfg_cls('foo', norm_cfg_cls)

        by_name = {
            field_analysis.field_desc.name: field_analysis
            for field_analysis in retval}
        assert not by_name['foo'].is_secret
        assert not by_name['bar'].is_secret
        assert by_name['baz'].is_secret
        assert not by_name['impl_foo'].is_secret
        assert by_name['impl_bar'].is_secret
        assert by_name['impl_bar'].is_concrete_only
        assert by_name['impl_foo'].is_concrete_only

    def test_explicit_sources_and_ttl(self):
        """Config fields with explicit sources declared must have those
        sources included in their analyses. The same goes for a
        refresh_after_max declaration.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        source1 = CfgSource('env', ('APP_SECRET_BAZ', 'DEPR_APP_SECRET_BAZ'))
        source2 = CfgSource('keychain', ('APP_SECRET_BAZ'))

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: str = ext_field(CfgField(
                source1,
                source2,
                refresh_after_max=12.34))

        norm_cfg_cls = NormalizedCfgCls(
            abstract_cls=FakeConfig,
            concrete_cls=FakeConfigImplementation)
        retval = analyze_cfg_cls('foo', norm_cfg_cls)

        by_name = {
            field_analysis.field_desc.name: field_analysis
            for field_analysis in retval}
        assert by_name['baz'].sources == (source1, source2)
        assert by_name['baz'].refresh_after_max == pytest.approx(12.34)
