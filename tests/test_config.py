'''
Module with tests for Config class
'''
import pytest

from rx_common  import Project, Qsq
from hqm.config import TransferFunctionMakerConf
from hqm.config import CCbarRatioCalculatorConf 

#----------------------------------
# Transfer function calculator
#----------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_unbinned_trfc(project : Project):
    '''
    Test configuration loader for unbinned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        variable = 'none',
        project  = project,
        source   = Qsq.psi2,
        target   = Qsq.high)

    assert len(cfgs) == 1

    print(cfgs[0])
#----------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_binned_trfc(project : Project):
    '''
    Test configuration loader for binned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        variable = 'nbrem',
        project  = project,
        source   = Qsq.psi2,
        target   = Qsq.high)

    assert len(cfgs) > 1

    for cfg in cfgs:
        print(cfg)
#----------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_per_bin_trfc(project : Project):
    '''
    Test configuration loader for single bin 
    '''
    cfg          = TransferFunctionMakerConf.load_bin_cfg(
        bin      = 1,
        variable = 'nbrem',
        project  = project,
        source   = Qsq.psi2,
        target   = Qsq.high)

    assert cfg.binning.bin == 1

    print(cfg)
#----------------------------------
# Ratio calculator
#----------------------------------
def test_unbinned_ratio():
    '''
    Test unbinned ratio calculator configuration
    '''
    cfgs = CCbarRatioCalculatorConf.load(variable = 'none')

    assert len(cfgs) == 1

    print(cfgs[0])
#----------------------------------
def test_binned_ratio():
    '''
    Test configuration loader for binned case
    '''
    cfgs = CCbarRatioCalculatorConf.load(variable = 'nbrem')
    assert len(cfgs) > 1

    for cfg in cfgs:
        print(cfg)
#----------------------------------
def test_pars():
    '''
    Test configuration loader for binned case
    '''
    cfgs = CCbarRatioCalculatorConf.load(variable = 'nbrem')
    cfg  = cfgs[0]

    for qsq in [Qsq.jpsi, Qsq.psi2]:
        obj_1 = cfg.parameters.get_ratio(qsq = qsq)
        obj_2 = cfg.parameters.get_ratio(qsq = qsq)

        assert obj_1 is obj_2

        obj_3 = cfg.parameters.get_part_reco_yield(qsq_comp = Qsq.jpsi, qsq_bin = qsq)
        obj_4 = cfg.parameters.get_part_reco_yield(qsq_comp = Qsq.jpsi, qsq_bin = qsq)

        assert obj_3 is obj_4

        obj_5 = cfg.parameters.get_part_reco_yield(qsq_comp = Qsq.psi2, qsq_bin = qsq)
        obj_6 = cfg.parameters.get_part_reco_yield(qsq_comp = Qsq.psi2, qsq_bin = qsq)

        assert obj_5 is obj_6
#----------------------------------
