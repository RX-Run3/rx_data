'''
Test for MVAConf class
'''
import pytest

from typing    import Final
from rx_common import MVAConf, MVAWp, UNINIT_VAL
from dmu       import LogStore

log = LogStore.add_logger('rx_common:test_mva_conf')

_WPS : Final[list[tuple[str,str]]] = [
    ('0100'     ,  'VAR >= 0.1'),
    ('0100-0300', '(VAR >= 0.1) && (VAR < 0.3)')]
'''Working point tuples for tests'''

_STR_VALS : Final[list[str]] = [val for val, _ in _WPS]
'''Working point string values for tests'''

_MIN_BOUND : Final[float] = 0.0
'''Minimum possible lower bound test value'''

_LOWER_BOUND : Final[float] = 0.1
'''Lower bound test value'''

_MID_BOUND : Final[float] = 0.2
'''Mid bound test value for lower range'''

_UPPER_BOUND : Final[float] = 0.3
'''Upper bound test value'''

_MAX_BOUND : Final[float] = 1.0
'''Maximum possible upper bound test value'''

_INVALID_STR_VAL : Final[str] = '20'
'''Invalid working point string value for tests'''

_CMB_VAR_NAME : Final[str] = 'mva_cmb'
'''CMB variable name for tests'''

_PRC_VAR_NAME : Final[str] = 'mva_prc'
'''PRC variable name for tests'''
# ----------------------------------------
def test_from_float():
    '''
    Test creating a config from floats
    '''
    cfg = MVAConf.from_values(cmb = _LOWER_BOUND, prc = _LOWER_BOUND)
    print('')
    print(cfg)
# ----------------------------------------
def test_from_tuple():
    '''
    Test creating a config from tuple 
    '''
    cfg = MVAConf.from_values(
        cmb = (_LOWER_BOUND, _UPPER_BOUND), 
        prc = _LOWER_BOUND)

    log.info('')
    log.info(cfg)
    log.info(cfg.cmb.get_cut(name = _CMB_VAR_NAME))
    log.info(cfg.prc.get_cut(name = _PRC_VAR_NAME))
# ----------------------------------------
@pytest.mark.parametrize('str_val', _STR_VALS)
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

    if str_val == _STR_VALS[0]:
        assert wp_1.lower == _LOWER_BOUND 
        assert wp_1.upper == _MAX_BOUND 

    if str_val == _STR_VALS[1]:
        assert wp_1.lower == _LOWER_BOUND 
        assert wp_2.upper == _UPPER_BOUND

    # Invalid string raises
    with pytest.raises(ValueError):
        MVAWp.from_str(val = _INVALID_STR_VAL)
# ----------------------------------------
@pytest.mark.parametrize('val, expr', _WPS)
def test_get_cut(val : str, expr : str):
    '''
    Test transforming string into floats
    '''
    var= _CMB_VAR_NAME
    wp = MVAWp.from_str(val = val)
    cut= wp.get_cut(name = var)

    expr = expr.replace('VAR', var)

    assert expr == cut
# ----------------------------------------
def test_none():
    '''
    Tests none class property meant to symbolize no cut
    '''
    wp_none = MVAWp.none()
    wp_valid= MVAWp(root = 0.5)

    assert wp_none.lower == UNINIT_VAL
    assert wp_none.upper == UNINIT_VAL
    assert wp_none       == MVAWp.none()
    assert wp_none       != wp_valid
# ----------------------------------------
