'''
Module with tests for DBMaker
'''
import pytest

from ROOT         import RDataFrame
from typing       import Any
from pathlib      import Path
from rx_selection import selection
from rx_common    import Trigger
from rx_common    import Component
from rx_data      import DBMaker, DBMakerConf
from rx_data      import db_maker

# -------------------------
class TestRDFGetter:
    '''
    Class meant to replace RDFGetter in tests
    '''
    def __init__(self, tree : Any, trigger : Any, sample : Any):
        pass

    def get_rdf(self, per_file : bool):
        _   = per_file

        rdf = RDataFrame(10_000)
        rdf = rdf.Define('mva_cmb', 'gRandom->Uniform(0, 1)')
        rdf = rdf.Define('mva_prc', 'gRandom->Gaus(0, 1)')

        return rdf
# -------------------------
def selector(
    q2bin   : Any,
    trigger : Any,
    process : Any,
    out_path: Any,
    rdf     : Any):

    _ = q2bin
    _ = trigger
    _ = process
    _ = out_path

    return rdf
# -------------------------
@pytest.fixture(autouse = False)
def _patch_rdfgetter(monkeypatch):
    monkeypatch.setattr(db_maker , 'RDFGetter'           , TestRDFGetter)
    monkeypatch.setattr(selection, 'apply_full_selection', selector)
# -------------------------------------
def test_simple(
    monkeypatch,
    _patch_rdfgetter,
    tmp_path : Path):
    '''
    Simplets test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    cfg = DBMakerConf(
        component    = Component.bpkpee,
        trigger      = Trigger.rk_ee_os,
        ncores       = 1,
        dropped_cuts = [])

    mkr = DBMaker(cfg = cfg)
    mkr.run()
# -------------------------------------
