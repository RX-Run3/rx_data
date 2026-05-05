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
@pytest.mark.parametrize('str_val', ['0.3', '0.1-0.2'])
def test_str_to_wp(str_val : str):
    '''
    Test transforming string into floats
    '''
    wp = MVAWp.from_str(val = str_val)
    if str_val == '0.3':
        assert wp.lower == 0.3 
        assert wp.upper == 1.0 

    if str_val == '0.1-0.2':
        assert wp.lower == 0.1 
        assert wp.upper == 0.2 

    # Invalid string raises
    with pytest.raises(ValueError):
        MVAWp.from_str(val = '200')
# ----------------------------------------
def test_label_to_wp():
    '''
    Test transforming string into floats
    '''
    # Single WP for both
    flt_val = 0.3
    int_val = int(flt_val * 100)
    str_val = f'{int_val:03d}' 

    wp = MVAWp.from_label(val = str_val)
    assert wp.lower == flt_val

    # Invalid string raises
    with pytest.raises(ValueError):
        MVAWp.from_label(val = '200')
# ----------------------------------------
