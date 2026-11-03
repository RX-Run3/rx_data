'''
Module with tests for selector class
'''
import os
from dataclasses         import dataclass
from importlib.resources import files

import pytest
from dmu.logging.log_store import LogStore
from ROOT                  import RDataFrame
from post_ap.selector      import Selector

log = LogStore.add_logger('post_ap:test_selector')
# --------------------------------------
@dataclass
class Data:
    '''
    Class used to store shared attributes
    '''
    mc_path : str
    dt_path : str
# --------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    config_path               = files('post_ap_data').joinpath('tests/post_ap.yaml')
    os.environ['CONFIG_PATH'] = str(config_path)

    LogStore.set_level('post_ap:selector'      , 10)
    LogStore.set_level('dmu:rdataframe:atr_mgr', 30)

    [Data.dt_path, Data.mc_path] = _get_paths()
# --------------------------------------
def _get_paths() -> list[str]:
    dt_path = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/dt_turbo.root'
    mc_path = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/bukmm_turbo.root'

    return [dt_path, mc_path]
# --------------------------------------
def _rename_branches(rdf : RDataFrame) -> RDataFrame:
    rdf = rdf.Define('B_const_mass_M', 'B_DTF_Jpsi_MASS')
    rdf = rdf.Define('H_TRACK_GhostProb' ,   'K_TRACK_GhostProb')

    return rdf
# --------------------------------------
def test_mc():
    '''
    Test selection in MC
    '''

    rdf = RDataFrame('Hlt2RD_BuToKpMuMu_MVA/DecayTree', Data.mc_path)
    rdf = _rename_branches(rdf)

    obj = Selector(rdf=rdf, is_mc=True)
    rdf = obj.run(sel_kind = 'bukmm')
    log.info('Saving output of test_mc')
    rdf.Snapshot('tree', '/tmp/selector_test.root', ['Jpsi_M'])
# --------------------------------------
def test_dt():
    '''
    Test selection in data
    '''

    rdf = RDataFrame('Hlt2RD_BuToKpMuMu_MVA/DecayTree', Data.dt_path)
    rdf = _rename_branches(rdf)

    obj = Selector(rdf=rdf, is_mc=False)
    rdf = obj.run(sel_kind = 'bukmm')
# --------------------------------------
def test_cfl():
    '''
    Test retrieving multiple dataframes, one after each cut
    '''

    rdf          = RDataFrame('Hlt2RD_BuToKpMuMu_MVA/DecayTree', Data.mc_path)
    rdf          = _rename_branches(rdf)

    obj   = Selector(rdf=rdf, is_mc=True)
    d_rdf = obj.run(sel_kind = 'bukmm', as_cutflow=True)

    for key, rdf in d_rdf.items():
        num = rdf.Count().GetValue()

        log.info(f'{key:<20}{num:<20}')
# --------------------------------------
@pytest.mark.parametrize('path', _get_paths())
def test_full(path : str):
    '''
    Test selection in MC
    '''
    config_path               = files('post_ap_data').joinpath('tests/post_ap_full.yaml')
    os.environ['CONFIG_PATH'] = str(config_path)

    rdf = RDataFrame('Hlt2RD_BuToKpMuMu_MVA/DecayTree', path)
    rdf = _rename_branches(rdf)

    obj = Selector(rdf=rdf, is_mc=True)
    rdf = obj.run(sel_kind = 'bukmm')
    log.info('Saving output of test_full')
    rdf.Snapshot('tree', '/tmp/selector_test.root', ['Jpsi_M'])
# --------------------------------------
