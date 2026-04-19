'''
Test for MVAConf class
'''
import pytest

from fitter    import MVAConf
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
def test_str_to_wp():
    '''
    Test transforming string into floats
    '''
    # Single WP for both
    flt_val = 0.3
    int_val = int(1000 * flt_val)
    str_val = str(int_val)

    assert MVAConf.str_to_wp(value = str_val) == flt_val

    # Invalid string raises
    with pytest.raises(ValueError):
        MVAConf.str_to_wp(value='2000')
# ----------------------------------------
