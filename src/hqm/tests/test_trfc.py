'''
Module holding tests for TransferFunctionMaker
'''
import pytest
import numpy

from collections.abc import Callable
from typing      import Any
from pathlib     import Path
from typing      import Final
from rx_common   import Project, Qsq
from dmu.generic import Mode
from hqm.trfc    import TransferFunctionMaker, TransferFunction
from hqm.config  import TransferFunctionMakerConf
from dmu         import LogStore
from dmu.stats   import zfit
from dmu.stats   import utilities as sut

log=LogStore.add_logger('rx_hqm:test_trfc')
obs : Final[zfit.Space] = zfit.Space("B_M", limits=(0, 7000))

type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space
#--------------------------------------
def set_log():
    LogStore.set_level('rx_scripts:zfitter'           , 20)
    LogStore.set_level('rx_hqm2:trfc'                 , 10)
    LogStore.set_level('rx_scripts:atr_mgr:mgr'       , 30)
    LogStore.set_level('rx_scripts:atr_mgr:ldr'       , 30)
    LogStore.set_level('rx_scripts:version_management', 30)
    LogStore.set_level('tools:calc_utility'           , 30)
#--------------------------------------
def _get_target_masses_low(self : Any, out_dir : Path) -> numpy.ndarray:
    _ = self
    _ = out_dir
    return numpy.random.normal(loc = 4750, scale = 80, size = 2000)
#--------------------------------------
def _get_target_masses_high(self : Any, out_dir : Path) -> numpy.ndarray:
    _ = self
    _ = out_dir
    return numpy.random.normal(loc = 5750, scale = 80, size = 2000)
#--------------------------------------
def _get_source_pdf(self : Any, obs : zobs, out_dir : Path) -> zpdf:
    _  = self
    _  = obs
    _  = out_dir

    mu = zfit.Parameter('mu', 5280, 5200, 5300)
    sg = zfit.Parameter('sg',   20,   10,   30)

    mu.floating = False
    sg.floating = False

    obs = zfit.Space('B_Mass', limits = (4000, 7500))

    return zfit.pdf.Gauss(obs = obs, mu = mu, sigma = sg)
#--------------------------------------
@pytest.fixture(autouse = False)
def _use_source_target(monkeypatch):
    monkeypatch.setattr(
        TransferFunctionMaker,
        '_TransferFunctionMaker__get_source_pdf',
        _get_source_pdf)
#--------------------------------------
@pytest.mark.parametrize('upper', [True, False])
def test_upper_lower(
    monkeypatch,
    upper : bool,
    _use_source_target : Callable,
    tmp_path : Path):
    '''
    Test moving PDF upper or lower
    '''
    _                  = _use_source_target
    _get_target_masses = _get_target_masses_high if upper else _get_target_masses_low
    source             = Qsq.jpsi if upper else Qsq.psi2
    target             = Qsq.psi2 if upper else Qsq.jpsi

    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(
        TransferFunctionMaker,
        '_TransferFunctionMaker__get_target_masses',
        _get_target_masses)

    cfg         = TransferFunctionMakerConf.load(
        binning = 'block-1 mva_cmb-3 mva_prc-2',
        project = Project.rk,
        source  = source,
        target  = target)

    obj         = TransferFunctionMaker(
        cfg     = cfg,
        project = Project.rk)

    trf = obj.get_trf(mode = Mode.write)

    path = tmp_path / 'transfer_function.json'
    trf.to_json(path = path)

    trf = TransferFunction.from_json(path)
    sut.print_pdf(trf.pdf)
#--------------------------------------
