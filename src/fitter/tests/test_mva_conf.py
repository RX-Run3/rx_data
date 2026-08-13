'''
Test for MVAConf class
'''
import pytest

from fitter    import MVAConf, MVAWp
from dmu       import LogStore

log = LogStore.add_logger('fitter:test_mva_conf')
# ----------------------------------------
def test_from_float():
    '''
    Test creating a config from floats
    '''
    cfg = MVAConf.from_values(cmb = 0.3, prc = 0.4)
    print('')
    print(cfg)
# ----------------------------------------
def test_from_tuple():
    '''
    Test creating a config from tuple 
    '''
    cfg = MVAConf.from_values(
        cmb = (0.2, 0.5), 
        prc = 0.4)
    log.info('')
    log.info(cfg)
    log.info(cfg.cmb.get_cut(name = 'mva_cmb'))
    log.info(cfg.prc.get_cut(name = 'mva_prc'))
# ----------------------------------------
@pytest.mark.parametrize('str_val', ['0300', '0100-0200'])
def test_str_to_wp(str_val : str):
    '''
    Test transforming string into floats
    '''
    wp_1 = MVAWp.from_str(val = str_val)
    # NOTE: Initialize through string only for tests
    # use from_str for actual code.
    # Tests needs to check that a string will be
    # usable as input to MVAWp 
    wp_2 = MVAWp(str_val) # type: ignore

    assert wp_1 == wp_2

    if str_val == '0300':
        assert wp_1.lower == 0.3 
        assert wp_1.upper == 1.0 

    if str_val == '0100-0200':
        assert wp_1.lower == 0.1 
        assert wp_2.upper == 0.2 

    # Invalid string raises
    with pytest.raises(ValueError):
        MVAWp.from_str(val = '200')
# ----------------------------------------
