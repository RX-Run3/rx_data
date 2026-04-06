'''
Module with tests for ScaleReader class
'''
import math
import pytest

from dmu       import LogStore
from fitter    import ScaleReader
from rx_common import Correction
from rx_common import Brem
from rx_common import Block 

log=LogStore.add_logger('fitter:test_scale_reader')

_CORRS = [
    Correction.mass_scale,
    Correction.mass_resolution,
]

_BLOCKS = Block.blocks()
# ----------------------
@pytest.mark.parametrize('kind' , _CORRS)
@pytest.mark.parametrize('block', _BLOCKS)
@pytest.mark.parametrize('brem' , [Brem.one, Brem.two, Brem.brx12])
def test_all(
    brem : Brem,
    block: Block,
    kind : Correction):
    '''
    Test all corrections
    '''
    srd      = ScaleReader()
    val, err = srd.get_scale(
        corr  = kind, 
        block = block, 
        brem  = brem)

    log.info('')
    log.info('kind:  %s', kind)
    log.info('val:   %s', val)
    log.info('err:   %s', err)
    log.info('block: %s', block)
    log.info('brem:  %s', brem)
    log.info('')

    assert isinstance(val, float)
    assert isinstance(err, float)

    assert not math.isnan(val)
    assert not math.isnan(err)
# ----------------------
@pytest.mark.parametrize('block', _BLOCKS)
@pytest.mark.parametrize('brem' , [Brem.one, Brem.two, Brem.brx12])
def test_single_block(
    brem : Brem,
    block: Block):
    '''
    Test block fraction correction
    '''
    srd      = ScaleReader()
    val, err = srd.get_scale(
        corr  = Correction.blok_fraction, 
        block = block, 
        brem  = brem)

    log.info('')
    log.info('val:   %s', val)
    log.info('err:   %s', err)
    log.info('block: %s', block)
    log.info('brem:  %s', brem)
    log.info('')

    assert isinstance(val, float)
    assert isinstance(err, float)

    assert not math.isnan(val)
    assert not math.isnan(err)
# ----------------------
