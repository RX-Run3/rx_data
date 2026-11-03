'''
Script with functions meant to test Enums
'''
import pytest

from functools import reduce
from operator  import add

from dmu       import LogStore
from rx_common import Correction
from rx_common import Component
from rx_common import Brem
from rx_common import Channel
from rx_common import Trigger
from rx_common import Project
from rx_common import Block

log=LogStore.add_logger('rx_common::test_types')

_COMPONENTS_WITH_DECAYS : list[Component] = [
    Component.bdkstkpiee,
    Component.bdkstkpimm,
    Component.bpkpjpsiee,
    Component.bpkpjpsimm]
# -------------------------------------------
@pytest.mark.parametrize('corr', Correction)
def test_correction(corr : Correction):
    '''
    Tests Correction type
    '''
    assert isinstance(corr.latex, str)
    assert corr.kind in {'reso', 'scale', 'weight'}
# -------------------------------------------
def test_component():
    '''
    Test Enum representing fit component
    '''
    assert Component.data_24.sample         == 'DATA_24*'

    assert Component.bpkpjpsiee.sample      == 'Bu_JpsiK_ee_eq_DPC'
    assert Component.bpkppsi2ee.sample      == 'Bu_psi2SK_ee_eq_DPC'
    assert Component.bppijpsiee.sample      == 'Bu_JpsiPi_ee_eq_DPC'
    # ------
    assert Component.bsphijpsimm.sample     == 'Bs_Jpsiphi_mm_eq_CPV_update2012_DPC'
    assert Component.bsphijpsiee.sample     == 'Bs_Jpsiphi_ee_eq_CPV_update2012_DPC'
    # ------
    assert Component.lbpkjpsimm.sample      == 'Lb_JpsipK_mm_eq_phsp_DPC'
    assert Component.lbpkjpsiee.sample      == 'Lb_JpsipK_ee_eq_phsp_DPC'
    # ------
    assert Component.bskstjpsimm.sample     == 'Bs_JpsiKst_mm_eq_DPC'
    assert Component.bskstjpsiee.sample     == 'Bs_JpsiKst_ee_eq_DPC'

    assert Component.bdkstkpijpsimm_kpimm_pikmm.sample == 'Bd_JpsiKst_mm_kpimm_pikmm'
    assert Component.bdkstkpijpsiee_kpiee_pikee.sample == 'Bd_JpsiKst_ee_kpiee_pikee'

    with pytest.raises(ValueError):
        assert Component.ccbar.sample           == 'ccbar'
# -------------------------------------------
def test_brem():
    '''
    Test for Enum representing brem
    '''
    assert str(Brem.zero) == 'brem_xx0'
    assert str(Brem.one)  == 'brem_xx1'
    assert str(Brem.two)  == 'brem_xx2'

    assert Brem.zero + Brem.one == Brem.br01x
    assert Brem.zero + Brem.two == Brem.br0x2
    assert Brem.one  + Brem.two == Brem.brx12

    assert Brem.zero + Brem.one + Brem.two == Brem.br012

    brems : list[Brem]

    with pytest.raises(TypeError):
        brems = []
        total = reduce(add, brems)

    brems = [Brem.one]
    total = reduce(add, brems)
    assert total == Brem.one

    brems = [Brem.one, Brem.two]
    total = reduce(add, brems)
    assert total == Brem.brx12

    brems = [Brem.zero, Brem.one, Brem.two]
    total = reduce(add, brems)
    assert total == Brem.br012
# -------------------------------------------
@pytest.mark.parametrize('sample', Component)
def test_sample_properties(sample : Component):
    '''
    Tests Sample enum properties
    '''
    assert isinstance(sample.name , str)
    assert isinstance(sample.latex, str)

    log.info(sample.name)
    log.info(sample.latex)
    log.info('')
# -------------------------------------------
def test_mc_samples():
    '''
    Tests that one can access list of MC samples
    '''
    mc_samples = Component.get_mc_samples()
    assert isinstance(mc_samples, list)
    assert mc_samples

    for sample in mc_samples:
        log.info(sample)
# -------------------------------------------
@pytest.mark.parametrize('sample', Component)
def test_channel(sample : Component):
    '''
    Tests channel property of samples
    '''
    if   sample.name.endswith('ee'):
        expected = Channel.ee
    elif sample.name.endswith('mm'):
        expected = Channel.mm
    else:
        expected = None

    if expected is not None:
        assert sample.channel == expected
        return
# -------------------------------------------
@pytest.mark.parametrize('trigger', Trigger)
def test_trigger(trigger : Trigger):
    '''
    Test trigger enum
    '''

    if   trigger.name.endswith('nopid') and trigger.name.startswith('rk_'):
        expected = Project.rk_no_pid
    elif trigger.name.endswith('nopid') and trigger.name.startswith('rkst_'):
        expected = Project.rkst_no_pid
    elif trigger.name.startswith('rk_'):
        expected = Project.rk
    elif trigger.name.startswith('rkst_'):
        expected = Project.rkst
    else:
        expected = None

    if expected is not None:
        assert trigger.project == expected
# -------------------------------------------
@pytest.mark.parametrize('sample', _COMPONENTS_WITH_DECAYS)
def test_subdecays(sample : Component):
    '''
    Tests access to subdecays from sample
    '''
    assert len(sample.subdecays) >= 1
    assert isinstance(sample.subdecays, list)
# -------------------------------------------
def test_block():
    '''
    Test block class
    '''
    for block in range(1, 9):
        Block(value = block)

    with pytest.raises(ValueError):
        Block(value = 11)

    with pytest.raises(ValueError):
        Block(value = 10)

    b1 = Block(value = 1)
    b2 = Block(value = 2)

    assert (b1 + b2) == Block(value = {1, 2})
    assert '1'       == str(b1)
    assert '2'       == str(b2)
    assert '12'      == str(b1 + b2)

    assert Block(value = -1).to_int() == -1
# -------------------------------------------
def test_block_from_str():
    '''
    Test block class
    '''
    for val in range(1, 9):
        assert Block.from_str(value = str(val)).to_int() == val

    assert Block.from_str(value = 'all').to_int() == -1
# -------------------------------------------
def test_block_dump():
    '''
    Test block class
    '''
    for block in range(1, 9):
        data = Block(value = block).model_dump()
        print(data)
# -------------------------------------------
