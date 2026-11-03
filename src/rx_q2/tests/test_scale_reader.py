'''
Module with tests for ScaleReader class
'''
import math
import pytest

from dmu       import LogStore
from rx_q2     import ScaleReader
from rx_common import Channel, Correction
from rx_common import Brem
from rx_common import Block

log=LogStore.add_logger('rx_q2:test_scale_reader')

_CORRS = [
    Correction.mass_scale,
    Correction.mass_resolution,
]

_PARS   = ['mu', 'sg']
_BLOCKS = Block.blocks()
# ----------------------
@pytest.mark.parametrize('kind' , _CORRS)
@pytest.mark.parametrize('block', _BLOCKS)
@pytest.mark.parametrize('brem' , [Brem.one, Brem.two, Brem.brx12])
def test_electron_scales(
    brem : Brem,
    block: Block,
    kind : Correction):
    '''
    Test all corrections
    '''
    srd      = ScaleReader(channel = Channel.ee)
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
@pytest.mark.parametrize('kind' , _CORRS)
@pytest.mark.parametrize('block', _BLOCKS)
def test_muon_scales(
    block: Block,
    kind : Correction):
    '''
    Test all corrections
    '''
    brem     = Brem.from_int(0)
    srd      = ScaleReader(channel = Channel.mm)
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
@pytest.mark.parametrize('is_mc' , [True, False])
@pytest.mark.parametrize('kind'  , _PARS)
@pytest.mark.parametrize('block' , _BLOCKS)
@pytest.mark.parametrize('brem'  , [Brem.one, Brem.two, Brem.brx12])
def test_electron_pars(
    is_mc: bool,
    brem : Brem,
    block: Block,
    kind : Correction):
    '''
    Test retrieval of parameters
    '''
    srd      = ScaleReader(channel = Channel.ee)
    val, err = srd.get_param(
        is_mc = is_mc,
        param = kind,
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
@pytest.mark.parametrize('is_mc' , [True, False])
@pytest.mark.parametrize('kind'  , _PARS)
@pytest.mark.parametrize('block' , _BLOCKS)
def test_muon_pars(
    is_mc: bool,
    block: Block,
    kind : Correction):
    '''
    Test retrieval of parameters
    '''
    brem     = Brem.from_int(0)
    srd      = ScaleReader(channel = Channel.mm)
    val, err = srd.get_param(
        is_mc = is_mc,
        param = kind,
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
def test_single_block_scales(
    brem : Brem,
    block: Block):
    '''
    Test block fraction correction
    '''
    srd      = ScaleReader(channel = Channel.ee)
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
