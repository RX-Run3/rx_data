'''
Module with tests for DataFitterSim class
'''
import pytest
import numpy

from typing      import Final
from functools   import cache
from rx_common   import Project
from pathlib     import Path
from dmu.stats   import ZFitPlotterConf
from rx_common   import Channel
from rx_common   import Component
from rx_common   import Trigger
from rx_common   import Brem
from rx_common   import Region
from rx_common   import Qsq
from rx_common   import MVAWp

from fitter      import CCbarConf
from fitter      import RXFitConfig
from fitter      import FitModelConf
from fitter      import NLLConf
from fitter      import DataFitterSim
from fitter      import PlotConf
from dmu.testing import get_nll 
from dmu.stats   import zfit
from dmu.generic import rxran

zpar = zfit.Parameter | zfit.ComposedParameter

_NEE : Final[int] = 10_000
_NMM : Final[int] = 30_000
# -------------------------------
@pytest.fixture(autouse = True)
def random_seed():
    with rxran.seed(value = 42):
        yield
# -------------------------------
@cache
def _get_pars() -> dict[str, zpar]:
    rat  = _NMM / _NEE
    rk   = zfit.Parameter('rk'  , rat, 0, 5)
    rkst = zfit.Parameter('rkst', rat, 0, 5)

    nkee   = zfit.Parameter('nsig_brem_x12-rk_ee_os'  , _NEE, 0, 100_000)
    nkstee = zfit.Parameter('nsig_brem_x12-rkst_ee_os', _NEE, 0, 100_000)

    def prod(pars : list[zpar]) -> zpar:
        return pars[0] * pars[1]

    nkmm   = zfit.ComposedParameter('nsig_brem_xx0-rk_mm_os'  , prod, params = [rk  , nkee  ])
    nkstmm = zfit.ComposedParameter('nsig_brem_xx0-rkst_mm_os', prod, params = [rkst, nkstee])

    pars = [nkee, nkstee, nkmm, nkstmm]

    return {par.name : par for par in pars} 
# -------------------------------
def _get_nll(region : Region) -> NLLConf:
    if region.trigger.is_electron:
        nentries = 2 * _NEE 
    else:
        nentries = 2 * _NMM 

    nll  = get_nll(
        nentries= nentries,
        kind    = 's+b',
        pars    = _get_pars(),
        suffix  = region.name)

    return NLLConf(
        nll         = nll,
        selection   = {},
        constraints = [])
# -------------------------------
def _get_cfg(region : Region) -> RXFitConfig:
    q2bin      = Qsq.central
    mva        = MVAWp.from_str(val = '0900')
    components = {q2bin : {Component.comb : CCbarConf.default(Channel.ee)}}
    plt_cfg    = PlotConf.default()
    plt_cfg    = plt_cfg.model_copy(update = {'regions' : {region : ZFitPlotterConf.default()}})

    new_fields = {
        'components' : components,
        'plots'      : {q2bin : plt_cfg} 
    }

    mod_cfg = FitModelConf.default()
    mod_cfg = mod_cfg.model_copy(update = {'trigger' : region.trigger})

    mod_cfg = mod_cfg.model_copy(update = new_fields)

    return RXFitConfig(
        name    = str(region),
        group   = 'test',
        q2bin   = q2bin,
        mva_cmb = mva,
        mva_prc = mva,
        mod_cfg = mod_cfg)
# -------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_single_ratio(
    monkeypatch,
    project  : Project,
    tmp_path : Path):
    '''
    Test electron and muon NLL combined
    '''
    monkeypatch.setenv('ANADIR', tmp_path)

    trg_ee  = Trigger.get_main_trigger(project = project, channel = Channel.ee)
    trg_mm  = Trigger.get_main_trigger(project = project, channel = Channel.mm)

    reg_ee  = Region(brem = Brem.brx12, trigger = trg_ee)
    reg_mm  = Region(brem = Brem.zero , trigger = trg_mm)
    regions = [reg_ee, reg_mm]

    d_nll : dict[Region, NLLConf] = {}
    for region in regions:
        d_nll[region] = _get_nll(region = region)

    d_cfg : dict[Region, RXFitConfig] = {}
    for region in regions:
        d_cfg[region] = _get_cfg(region = region)

    ftr = DataFitterSim(
        d_cfg = d_cfg,
        d_nll = d_nll, 
        q2bin = Qsq.central)

    res = ftr.run(skip_fit = False)

    print(res)
# -------------------------------
def test_double_ratio(monkeypatch, tmp_path : Path):
    '''
    Test electron and muon NLL combined
    '''
    monkeypatch.setenv('ANADIR', tmp_path)

    rk_ee   = Region(brem = Brem.brx12, trigger = Trigger.rk_ee_os)
    rk_mm   = Region(brem = Brem.zero , trigger = Trigger.rk_mm_os)

    rkst_ee = Region(brem = Brem.brx12, trigger = Trigger.rkst_ee_os)
    rkst_mm = Region(brem = Brem.zero , trigger = Trigger.rkst_mm_os)

    regions = [rk_ee, rk_mm, rkst_ee, rkst_mm]

    d_nll : dict[Region, NLLConf] = {}
    for region in regions:
        d_nll[region] = _get_nll(region = region)

    d_cfg : dict[Region, RXFitConfig] = {}
    for region in regions:
        d_cfg[region] = _get_cfg(region = region)

    ftr = DataFitterSim(
        d_cfg = d_cfg,
        d_nll = d_nll, 
        q2bin = Qsq.central)
    res = ftr.run(skip_fit = False)

    rk  , _ = res.get('rk'  , fall_back=None)
    rkst, _ = res.get('rkst', fall_back=None)

    assert numpy.isclose(rk  , 3.04176)
    assert numpy.isclose(rkst, 2.99603)

    print(res)
# -------------------------------
