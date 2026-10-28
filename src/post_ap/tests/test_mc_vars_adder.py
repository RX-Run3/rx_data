'''
Module containing tests for MCVarsAdder class
'''
import numpy
import pytest

from ROOT                    import RDF
from dmu                     import LogStore
from post_ap.mc_vars_adder   import MCVarsAdder

log = LogStore.add_logger('post_ap:test_mc_vars_adder')
_SAMPLES=[
    'mc_24_w40_41_magdown_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w40_41_magdown_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w40_41_magdown_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w40_41_magdown_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w41_42_magup_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w41_42_magup_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w41_42_magup_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
    'mc_24_w41_42_magup_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w41_42_magup_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w41_42_magup_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w41_42_magup_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w31_magup_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w31_magup_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w31_magup_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
    'mc_24_w31_magup_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w31_magup_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w31_magup_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w31_magup_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w32_34_magup_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w32_34_magup_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w32_34_magup_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
    'mc_24_w32_34_magup_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w32_34_magup_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w32_34_magup_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w32_34_magup_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w35_37_magup_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w40_41_magdown_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w40_41_magdown_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w40_41_magdown_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
    'mc_24_w35_37_magup_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w35_37_magup_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
    'mc_24_w35_37_magup_sim10f_12143001_bu_jpsik_mm_eq_dpc_tuple',
    'mc_24_w35_37_magup_sim10f_12153001_bu_jpsik_ee_eq_dpc_tuple',
    'mc_24_w35_37_magup_sim10f_12583022_bu_d0enu_kenu_eq_tc_tuple',
    'mc_24_w35_37_magup_sim10f_13144025_bs_jpsikst_update2012_mm_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_11144001_bd_jpsikst_mm_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_11154001_bd_jpsikst_ee_eq_dpc_tuple',
    'mc_24_w37_39_magdown_sim10f_12125000_bu_kpipiee_eq_dpc_lsflat_tuple',
]
# -------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    LogStore.set_level('post_ap:mc_vars_adder'     , 10)
    LogStore.set_level('post_ap:test_mc_vars_adder', 10)
# -------------------------------------------------
@pytest.mark.parametrize('sample', _SAMPLES)
def test_simple(sample : str):
    '''
    Simplest test
    '''
    rdf = RDF.FromNumpy({'B_PT' : numpy.random.uniform(0, 10_000, 10_000)})

    obj = MCVarsAdder(
        sample_name = sample,
        rdf         = rdf)

    rdf       = obj.get_rdf()
    arr_block = rdf.AsNumpy(['block'])['block']

    assert any( block in arr_block for block in range(1,9) )
# -------------------------------------------------
