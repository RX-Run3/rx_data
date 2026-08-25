'''
Module with tests for DatabaseBuilder class
'''
import pytest

from ROOT                 import RDF  # type: ignore
from pathlib              import Path
from rx_common            import Component, Trigger
from hqm.database_builder import DatabaseBuilder
from hqm.database_conf    import DatabaseConf

from .utilities           import get_data
# ------------------------------------
def _get_rdf(self) -> RDF.RNode:
    data = get_data()

    return RDF.FromNumpy(data)
# ------------------------------------
@pytest.fixture(autouse = False)
def _patch_rdfgetter(monkeypatch):
    monkeypatch.setattr(
        DatabaseBuilder,
        '_DatabaseBuilder__get_rdf',
        _get_rdf)
# ------------------------------------
def test_simple(
    _patch_rdfgetter, 
    monkeypatch,
    tmp_path : Path):

    monkeypatch.setenv('ANADIR', str(tmp_path))

    trig = Trigger.rk_ee_os
    comp = Component.bpkpjpsimm
    cfg  = DatabaseConf.load()

    obj = DatabaseBuilder(
        trig = trig,
        comp = comp,
        cfg  = cfg)

    obj.run()
# ------------------------------------
