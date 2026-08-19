
import matplotlib.pyplot as plt
import mplhep
import pytest
import numpy
import zfit

from pathlib     import Path
from typing      import Final
from rx_common   import Block, Component, Project, Qsq
from hqm.trfc    import TransferFunctionMaker 
from hqm.config  import Conf
from dmu         import LogStore

log=LogStore.add_logger('rx_hqm:test_trfc')
obs : Final[zfit.Space] = zfit.Space("B_M", limits=(0, 7000))
#--------------------------------------
def set_log():
    LogStore.set_level('rx_scripts:zfitter'           , 20)
    LogStore.set_level('rx_hqm2:trfc'                 , 10)
    LogStore.set_level('rx_scripts:atr_mgr:mgr'       , 30)
    LogStore.set_level('rx_scripts:atr_mgr:ldr'       , 30)
    LogStore.set_level('rx_scripts:version_management', 30)
    LogStore.set_level('tools:calc_utility'           , 30)
#--------------------------------------
def _get_masses(self, is_source : bool) -> numpy.ndarray:
    if is_source:
        return numpy.random.normal(loc = 5280, scale = 20, size = 2000)

    return numpy.random.normal(loc = 5200, scale = 30, size = 2000)
#--------------------------------------
@pytest.fixture(autouse = True)
def _use_fake_masses(monkeypatch):
    monkeypatch.setattr(
        TransferFunctionMaker,
        '_TransferFunctionMaker__get_masses',
        _get_masses)
#--------------------------------------
def test_psi2_high_brem(monkeypatch, tmp_path : Path):
    '''
    Basic test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    cfgs        = Conf.load(
        binning = 'none', 
        source  = Qsq.psi2,
        target  = Qsq.high) 

    obj         = TransferFunctionMaker(
        cfg     = cfgs[0],
        sample  = Component.bpkpjpsimm, 
        project = Project.rk,
        block   = Block(value = 1) )

    obj.get_trf()
#--------------------------------------
def test_psi2_high():
    obj     = TransferFunctionMaker(obs=data.obs, source='psi2', target='high', sample='psi2', trigger='2018', prefix='psi2_high_pr_2018')
    obj.get_trf()
#--------------------------------------
def test_jpsi_high():
    obj     = TransferFunctionMaker(obs=data.obs, source='jpsi', target='high', sample='ctrl', trigger='comb', prefix='jpsi_high_pr_comb')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_jpsi_jpsi():
    obj     = TransferFunctionMaker(obs=data.obs, source='jpsi', target='jpsi', sample='ctrl', trigger='2018', prefix='jpsi_jpsi_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_jpsi_psi2():
    obj     = TransferFunctionMaker(obs=data.obs, source='jpsi', target='psi2', sample='ctrl', trigger='2018', prefix='jpsi_psi2_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_psi2_jpsi():
    obj     = TransferFunctionMaker(obs=data.obs, source='psi2', target='jpsi', sample='psi2', trigger='2018', prefix='psi2_jpsi_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_psi2_psi2():
    obj     = TransferFunctionMaker(obs=data.obs, source='psi2', target='psi2', sample='psi2', trigger='2018', prefix='psi2_psi2_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def main():
    set_log()
    plt.style.use(mplhep.style.LHCb2)

    test_jpsi_high()
    test_psi2_high()

    test_psi2_high_brem(0)
    test_psi2_high_brem(1)
    test_psi2_high_brem(2)

    test_jpsi_jpsi()
    test_psi2_psi2()
    test_jpsi_jpsi()
    test_psi2_psi2()
    test_jpsi_jpsi()
    test_jpsi_psi2()
    test_psi2_jpsi()
#--------------------------------------
if __name__ == '__main__':
    main()

