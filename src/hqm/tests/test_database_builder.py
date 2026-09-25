'''
Module with tests for DatabaseBuilder class
'''
import pytest

from dmu                  import LogStore
from ROOT                 import RDF  # type: ignore
from typing               import Any
from pathlib              import Path
from rx_common            import Channel, Component, Trigger
from collections.abc      import Callable
from hqm.database_builder import DatabaseBuilder
from hqm.database_conf    import DatabaseConf
from hqm.utilities        import get_data

# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('hqm:database_builder', 10)
# ------------------------------------
def _get_rdf(self : Any) -> RDF.RNode:
    _    = self
    data = get_data(channel = Channel.ee)

    return RDF.FromNumpy(data)
# ------------------------------------
@pytest.fixture(autouse = False)
def _patch_rdfgetter(monkeypatch):
    monkeypatch.setattr(
        DatabaseBuilder,
        '_DatabaseBuilder__get_rdf',
        _get_rdf)
# ------------------------------------
@pytest.mark.parametrize('comp', [Component.data_24, Component.bpkpjpsiee])
def test_simple(
    monkeypatch,
    _patch_rdfgetter : Callable,
    comp             : Component,
    tmp_path         : Path):

    _ = _patch_rdfgetter
    monkeypatch.setenv('ANADIR', str(tmp_path))

    trig = Trigger.rk_ee_os
    cfg  = DatabaseConf.load()

    obj = DatabaseBuilder(
        trig = trig,
        comp = comp,
        cfg  = cfg)

    obj.run()
# ------------------------------------
