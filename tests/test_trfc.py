'''
Module holding tests for TransferFunctionMaker
'''
import pytest
import numpy

from pathlib     import Path
from typing      import Final
from rx_common   import Block, Project, Qsq
from hqm.trfc    import TransferFunctionMaker, TransferFunction
from hqm.config  import TransferFunctionMakerConf
from dmu         import LogStore
from dmu.stats   import zfit
from dmu.stats   import utilities as sut

log=LogStore.add_logger('rx_hqm:test_trfc')
obs : Final[zfit.Space] = zfit.Space("B_M", limits=(0, 7000))

zpdf = zfit.pdf.BasePDF
#--------------------------------------
def set_log():
    LogStore.set_level('rx_scripts:zfitter'           , 20)
    LogStore.set_level('rx_hqm2:trfc'                 , 10)
    LogStore.set_level('rx_scripts:atr_mgr:mgr'       , 30)
    LogStore.set_level('rx_scripts:atr_mgr:ldr'       , 30)
    LogStore.set_level('rx_scripts:version_management', 30)
    LogStore.set_level('tools:calc_utility'           , 30)
#--------------------------------------
def _get_target_masses(self) -> numpy.ndarray:
    return numpy.random.normal(loc = 5200, scale = 30, size = 2000)
#--------------------------------------
def _get_source_pdf(self, path : Path) -> zpdf:
    mu = zfit.Parameter('mu', 5280, 5200, 5300)
    sg = zfit.Parameter('sg',   20,   10,   30)

    mu.floating = False
    sg.floating = False

    obs = zfit.Space('B_Mass', limits = (4800, 5800))

    return zfit.pdf.Gauss(obs = obs, mu = mu, sigma = sg)
#--------------------------------------
@pytest.fixture(autouse = False)
def _use_source_target(monkeypatch):
    monkeypatch.setattr(
        TransferFunctionMaker,
        '_TransferFunctionMaker__get_target_masses',
        _get_target_masses)

    monkeypatch.setattr(
        TransferFunctionMaker,
        '_TransferFunctionMaker__get_source_pdf',
        _get_source_pdf)
#--------------------------------------
def test_psi2_high_brem(
    monkeypatch,
    _use_source_target,
    tmp_path : Path):
    '''
    Basic test with fake data
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    cfgs        = TransferFunctionMakerConf.load(
        variable= 'none',
        project = Project.rk,
        source  = Qsq.psi2,
        target  = Qsq.high)

    obj         = TransferFunctionMaker(
        cfg     = cfgs[0],
        project = Project.rk,
        block   = Block(value = 1) )

    trf = obj.get_trf(update = True)

    path = tmp_path / 'transfer_function.json'
    trf.to_json(path = path)

    trf = TransferFunction.from_json(path)
    sut.print_pdf(trf.pdf)
#--------------------------------------
