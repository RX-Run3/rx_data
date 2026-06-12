'''
File containing tests for FilterFile class
'''
import os
import glob
import shutil
from importlib.resources   import files

import pytest
from ROOT                  import RDataFrame
from dmu.logging.log_store import LogStore
from dmu.generic           import version_management as vmn
from post_ap.filter_file   import FilterFile


log = LogStore.add_logger('post_ap:test_filter_file')
# --------------------------------------
class Data:
    '''
    Data class with shared attributes
    '''
    mc_turbo_mm    = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/mc_24_w31_34_magup_sim10d_12113002_bu_kmumu_eq_btosllball05_dpc_tuple.root'
    mc_turbo_ee    = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/mc_24_w35_37_magup_sim10d_12123003_bu_kee_eq_btosllball05_dpc_tuple.root'

    mc_test_spruce   = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/mc_spruce.root'

    data_test_turbo  = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/dt_turbo.root'
    data_test_spruce = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/dt_spruce.root'

    output_dir       = '/tmp/post_ap/tests/filter_file'
    l_pv_sv          = ['B_BPVX', 'B_BPVY', 'B_BPVZ', 'B_END_VX', 'B_END_VY', 'B_END_VZ']
    l_rpk_mm         = [
            'Lb_DTF_CHI2DOF',
            'Lb_P',
            'Lb_PT',
            'K_PT',
            'K_ETA',
            'P_PID_K',
            'Lz_BPVIPCHI2',
            'Lz_PT',
            'Lz_END_VCHI2DOF',
            'P_PT',
            'P_ETA',
            'P_PID_P',
            'P_BPVIPCHI2',
            'L1_PT',
            'L1_PIDmu',
            'L2_PT',
            'L2_PIDmu',
            'Jpsi_PT',
            'Jpsi_BPVIPCHI2',
            'Jpsi_BPVFDCHI2',
            'Jpsi_END_VCHI2DOF',
            'nTracks',
            ]

    d_branch_names   = {
            'test_rpk_mm_mc' : l_rpk_mm,
            'test_rpk_mm_dt' : l_rpk_mm,
            'test_mc'        : l_pv_sv,
            'test_dt'        : l_pv_sv,
            }

    l_args_config    = [True, False]
# --------------------------------------
def _check_branches(rdf : RDataFrame, file_path : str, is_reco : bool, test_name : str) -> None:
    nentries = rdf.Count().GetValue()
    if nentries == 0:
        log.warning(f'No entries found in: {file_path}')
        return

    l_has_to_exist = ['block', 'EVENTNUMBER']

    if is_reco and test_name in Data.d_branch_names:
        l_has_to_exist += Data.d_branch_names[test_name]
    else:
        l_has_to_exist += []

    if not test_name.endswith('_mc'):
        l_has_to_exist += ['RUNNUMBER']

    fail  = False
    l_col = [ name.c_str() for name in rdf.GetColumnNames() ]
    for has_to_exist in l_has_to_exist:
        if has_to_exist not in l_col:
            fail=True
            log.error(f'{has_to_exist} branch missing in: {file_path}')

    if fail:
        raise ValueError('At least one branch was not found')
# --------------------------------------
def _check_file(file_path : str, is_mc : bool, test_name : str) -> None:
    rdf_dt = RDataFrame('DecayTree'  , file_path)
    _check_branches(rdf_dt, file_path, test_name = test_name, is_reco = True)

    if not is_mc:
        return

    rdf_mc = RDataFrame('MCDecayTree', file_path)
    _check_branches(rdf_mc, file_path, test_name = test_name, is_reco = False)
# --------------------------------------
def _move_outputs(test_name : str, is_mc : bool) -> None:
    l_root = glob.glob('*.root')

    for path in l_root:
        _check_file(path, is_mc, test_name)

    l_text = glob.glob('*.txt' )
    l_path = l_root + l_text
    npath  = len(l_path)

    target_dir = f'{Data.output_dir}/{test_name}'
    log.info(f'Moving {npath} to {target_dir}')
    os.makedirs(target_dir, exist_ok=True)
    for source in l_path:
        file_name = os.path.basename(source)
        shutil.move(source, f'{target_dir}/{file_name}')
# --------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    Will set loggers, etc
    '''
    log.info('Initializing')

    cfg_dir  = files('post_ap_data').joinpath('post_ap/rx')
    cfg_path = vmn.get_latest_file(dir_path = str(cfg_dir), wc='v*.yaml')

    os.environ['CONFIG_PATH'] = str(cfg_path)

    LogStore.set_level('dmu:rdataframe:atr_mgr', 30)
    LogStore.set_level('post_ap:selector'      , 20)
    LogStore.set_level('post_ap:utilities'     , 30)
    LogStore.set_level('post_ap:FilterFile'    , 20)
    LogStore.set_level('post_ap:mc_vars_adder' , 20)
# --------------------------------------
@pytest.mark.parametrize('kind' , ['turbo'])
def test_dt(kind : bool):
    '''
    Run test on data
    '''
    sample_name = 'data_test'
    path        = getattr(Data, f'{sample_name}_{kind}')

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 10000
    obj.max_save       = 1000
    obj.run()

    _move_outputs('test_dt', is_mc = False)
# --------------------------------------
@pytest.mark.parametrize('nickname', ['mc_turbo_ee', 'mc_turbo_mm'])
def test_mc(nickname : str):
    '''
    Run test on MC
    '''
    path        = getattr(Data, nickname)
    fname       = os.path.basename(path)
    sample_name = fname.replace('.root', '')

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       = 1000
    obj.run()

    _move_outputs('test_mc', is_mc = True)
# --------------------------------------
def test_bad_mcdt():
    '''
    Run test on MC with broken MCDT
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/mc_bad_mcdt.root'
    sample_name = 'mc_24_w35_37_magup_sim10d_15124011_lb_pkee_eq_phsp_dpc_tuple'

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run()

    _move_outputs('test_bad_mcdt', is_mc = True)
# --------------------------------------
def test_rpk_ee_mc():
    '''
    Run test on MC for RpK electron sample
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_ee_mc.root'
    sample_name = 'mc_24_w35_37_magup_sim10d_15124011_lb_pkee_eq_phsp_dpc_tuple'

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run()

    _move_outputs('test_rpk_ee_mc', is_mc = True)
# --------------------------------------
def test_rpk_mm_mc():
    '''
    Run test on MC for RpK muon sample
    '''
    path        = '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_mm_mc.root'
    sample_name = 'mc_24_w37_39_magdown_sim10d_15114011_lb_pkmumu_eq_phsp_dpc_tuple'

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run()

    _move_outputs('test_rpk_mm_mc', is_mc = True)
# --------------------------------------
def test_rpk_dt():
    '''
    Run test on data for RpK
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_data.root'

    obj = FilterFile(sample_name='data_rpk_test', file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_rpk_dt', is_mc = False)
# --------------------------------------
