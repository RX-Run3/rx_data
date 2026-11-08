'''
Module holding tests for Component Enum
'''
import pytest

from rx_common import Component
from dmu       import LogStore


log=LogStore.add_logger('rx_common::test_component')

_COMPONENTS_WITH_DECAYS : list[Component] = [
    Component.bdkstkpiee,
    Component.bdkstkpimm,
    Component.bpkpjpsiee,
    Component.bpkpjpsimm]
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
@pytest.mark.parametrize('sample', _COMPONENTS_WITH_DECAYS)
def test_subdecays(sample : Component):
    '''
    Tests access to subdecays from sample
    '''
    assert len(sample.subdecays) >= 1
    assert isinstance(sample.subdecays, list)
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
def test_sample_properties(sample : Component):
    '''
    Tests Sample enum properties
    '''
    assert isinstance(sample.name , str)
    assert isinstance(sample.latex, str)

    log.info(sample.name)
    log.info(sample.latex)
    log.info('')

