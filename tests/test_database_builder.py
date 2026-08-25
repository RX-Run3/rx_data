'''
Module with tests for DatabaseBuilder class
'''
import pytest
import numpy

from typing               import Final
from ROOT                 import RDF  # type: ignore
from pathlib              import Path
from rx_common            import Component, Trigger, Mass
from hqm.database_builder import DatabaseBuilder, DatabaseBuilderConf

_SIZE : Final[int] = 10_000
# ------------------------------------
def _get_rdf(self) -> RDF.RNode:
    data = {
        Mass.bp_bcor.value     : numpy.random.uniform(3000, 5100, _SIZE),
        Mass.bp_dtf_jpsi.value : numpy.random.normal(loc = 5200, scale = 20, size = _SIZE),
        Mass.bp_dtf_psi2.value : numpy.random.normal(loc = 5200, scale = 20, size = _SIZE),
    }

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
    cfg  = DatabaseBuilderConf.load()

    obj = DatabaseBuilder(
        trig = trig,
        comp = comp,
        cfg  = cfg)

    obj.run()
# ------------------------------------
