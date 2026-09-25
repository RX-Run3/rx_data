'''
Module with tests for CCbarRatioCalculator class
'''
import pytest

from typing      import Any
from dmu.generic import Mode
from typing      import Final
from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import zfit
from rx_common   import Component, Project, Qsq
from hqm.config  import CCbarRatioCalculatorConf
from hqm.ratc    import CCbarRatioCalculator

type zpdf = zfit.pdf.BasePDF

# Part reco / Fully reco
_RJPSI      : Final[float]              = 0.8
_RPSI2      : Final[float]              = 0.3
_REAL_FACTOR: Final[int  ]              = 1000 # Scale factor for synthetic version of real data
_OBS_RANGE  : Final[tuple[float,float]] = 4600, 7000

log=LogStore.add_logger('hqm:test_ratc')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('hqm:data_store', 30)
    LogStore.set_level('hqm:ratc'      , 10)
    LogStore.set_level('hqm:config'    , 10)
#-------------------------------------
def _get_fr_entries(qsq_src : Qsq, qsq_tgt : Qsq) -> int:
    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.jpsi:
        return  40 * _REAL_FACTOR

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.jpsi:
        return   5 * _REAL_FACTOR

    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.psi2:
        return  10 * _REAL_FACTOR

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.psi2:
        return  10 * _REAL_FACTOR

    raise ValueError('Invalid q2')
#-------------------------------------
def _get_pr_shape(self : Any, qsq_src : Qsq, qsq_tgt : Qsq) -> tuple[float,float]:
    _  = self
    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.jpsi:
        return 5100, 150

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.jpsi:
        return 4700, 150

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.psi2:
        return 5000, 150

    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.psi2:
        return 4700, 150

    raise ValueError(f'Invalid q2 bin: {qsq_src}')
#-------------------------------------
def _get_fr_shape(self : Any, comp : Component, qsq : Qsq) -> tuple[float,float]:
    _  = self
    jj = comp == Component.bpkpjpsiee and qsq == Qsq.jpsi
    pj = comp == Component.bpkppsi2ee and qsq == Qsq.jpsi

    jp = comp == Component.bpkpjpsiee and qsq == Qsq.psi2
    pp = comp == Component.bpkppsi2ee and qsq == Qsq.psi2

    if jj or pp:
        mu = 5300
        sg = 50
    elif pj:
        mu = 4900
        sg = 50
    elif jp:
        mu = 6000
        sg =150
    else:
        raise ValueError(f'Invalid component/qsq: {comp}/{qsq}')

    return mu, sg
#--------------------------------------
def _get_mc_pdf(
    self    : Any,
    comp    : Component,
    qsq_src : Qsq,
    qsq_tgt : Qsq) -> zpdf:
    _  = self
    _  = qsq_src
    _  = qsq_tgt

    mu, sg = _get_fr_shape(self = 1, comp = comp, qsq = qsq_tgt)

    obs = zfit.Space('B_Mass', limits = _OBS_RANGE)
    mu  = zfit.Parameter(f'mu_{comp}_{qsq_tgt}', mu, 4000, 7000)
    sg  = zfit.Parameter(f'sg_{comp}_{qsq_tgt}', sg,    0, 300)

    mu.floating = False
    sg.floating = False

    pdf = zfit.pdf.Gauss(
        name  = comp,
        mu    = mu,
        sigma = sg,
        obs   = obs)

    return pdf
#-------------------------------------
def _get_mu_sg(qsq_src: Qsq, qsq_tgt: Qsq) -> tuple[float, float]:
    if   qsq_src == Qsq.jpsi and qsq_tgt == Qsq.jpsi:
        return -80, 20
    elif qsq_src == Qsq.jpsi and qsq_tgt == Qsq.psi2:
        return 20, 40
    elif qsq_src == Qsq.psi2 and qsq_tgt == Qsq.jpsi:
        return -120, 40
    elif qsq_src == Qsq.psi2 and qsq_tgt == Qsq.psi2:
        return -80, 20
    else:
        raise ValueError(f"Invalid qsq combination: {qsq_src=}, {qsq_tgt=}")
#-------------------------------------
def _get_pr_pdf(self : Any, qsq_src : Qsq, qsq_tgt : Qsq) -> zpdf:
    _  = self
    mu, sg      = _get_pr_shape(
        self    = 1,
        qsq_src = qsq_src,
        qsq_tgt = qsq_tgt)

    obs = zfit.Space('B_Mass', limits = _OBS_RANGE)
    mu  = zfit.Parameter(f'mu_{qsq_src}_{qsq_tgt}', mu, 4000, 7000)
    sg  = zfit.Parameter(f'sg_{qsq_src}_{qsq_tgt}', sg,    0, 300)

    mu.floating = False
    sg.floating = False

    pdf = zfit.pdf.Gauss(
        name  = f'{qsq_src}_{qsq_tgt}',
        mu    = mu,
        sigma = sg,
        obs   = obs)

    return pdf
#--------------------------------------
@pytest.fixture(autouse = True)
def _use_fake_masses(monkeypatch):
    monkeypatch.setattr(
        CCbarRatioCalculator,
        '_CCbarRatioCalculator__get_mc_pdf',
        _get_mc_pdf)

    monkeypatch.setattr(
        CCbarRatioCalculator,
        '_CCbarRatioCalculator__get_pr_pdf',
        _get_pr_pdf)
#-------------------------------------
def test_unbinned(monkeypatch, tmp_path : Path):
    '''
    Test in unbinned case
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    binning= 'block-1 mva_cmb-7 mva_prc-7'
    cfg    = CCbarRatioCalculatorConf.load(binning = 'block-1')

    cal         = CCbarRatioCalculator(
        cfg     = cfg,
        binning = binning,
        ntoys   = 50_000,
        project = Project.rk)

    ratio    = cal.get_ratio(mode = Mode.write)
    val, err = ratio.get_value(name = 'rat_psi2')

    assert isinstance(val, float)
    assert isinstance(err, float)
#-------------------------------------
