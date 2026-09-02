'''
Module with tests for CCbarRatioCalculator class
'''
import pytest
import numpy

from typing      import Final
from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import zfit
from rx_common   import Block, Component, Project, Qsq
from hqm.config  import CCbarRatioCalculatorConf
from hqm.ratc    import CCbarRatioCalculator

type zpdf = zfit.pdf.BasePDF

# Part reco / Fully reco
_RJPSI      : Final[float]              = 0.5
_RPSI2      : Final[float]              = 0.5
_REAL_FACTOR: Final[int  ]              = 10_000 # Scale factor for synthetic version of real data
_OBS_RANGE  : Final[tuple[float,float]] = 4000, 7000

log=LogStore.add_logger('hqm:test_ratc')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_hqm2:data_store', 30)
    LogStore.set_level('rx_hqm:config'     , 10)
#-------------------------------------
def _get_fr_entries(qsq_src : Qsq, qsq_tgt : Qsq) -> int:
    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.jpsi:
        return 10 * _REAL_FACTOR

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.jpsi:
        return  1 * _REAL_FACTOR

    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.psi2:
        return  2 * _REAL_FACTOR

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.psi2:
        return  2 * _REAL_FACTOR

    raise ValueError('Invalid q2')
#-------------------------------------
def _get_fr_shape(self, comp : Component, qsq : Qsq) -> tuple[float,float]:
    jj = comp == Component.bpkpjpsiee and qsq == Qsq.jpsi
    pp = comp == Component.bpkppsi2ee and qsq == Qsq.psi2

    jp = comp == Component.bpkpjpsiee and qsq == Qsq.psi2
    pj = comp == Component.bpkppsi2ee and qsq == Qsq.jpsi

    if jj or pp:
        mu = 5280
        sg = 100
    elif jp:
        mu = 6000
        sg = 150
    elif pj:
        mu = 4900
        sg = 150
    else:
        raise ValueError(f'Invalid component/qsq: {comp}/{qsq}')

    return mu, sg
#--------------------------------------
def _get_mc_pdf(self, comp : Component, qsq : Qsq) -> zpdf:
    mu, sg = _get_fr_shape(self = 1, comp = comp, qsq = qsq)

    obs = zfit.Space('B_Mass', limits = _OBS_RANGE)
    mu  = zfit.Parameter(f'mu_{comp}_{qsq}', mu, 4800, 6200)
    sg  = zfit.Parameter(f'sg_{comp}_{qsq}', sg,    0, 300)

    mu.floating = False
    sg.floating = False

    pdf = zfit.pdf.Gauss(
        name  = comp,
        mu    = mu,
        sigma = sg,
        obs   = obs)

    return pdf
#-------------------------------------
def _get_pr_shape(self, qsq : Qsq) -> tuple[float,float]:
    if qsq == Qsq.jpsi:
        return 4700,  50 

    if qsq == Qsq.psi2:
        return 5000, 150 

    raise ValueError(f'Invalid q2 bin: {qsq}')
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
def _get_target_data(self, qsq : Qsq) -> numpy.ndarray:
    obs       = zfit.Space('B_Mass', limits = (3000, 8000))
    size_jx   = _get_fr_entries(qsq_src=Qsq.jpsi, qsq_tgt=qsq)
    size_px   = _get_fr_entries(qsq_src=Qsq.psi2, qsq_tgt=qsq)
    # ------
    pdf_fr_jp = _get_mc_pdf(self = 1, comp=Component.bpkpjpsiee, qsq=qsq)
    pdf_fr_ps = _get_mc_pdf(self = 1, comp=Component.bpkppsi2ee, qsq=qsq)

    jpsi_fr   = pdf_fr_jp.create_sampler(n = size_jx, limits = obs).numpy()
    psi2_fr   = pdf_fr_ps.create_sampler(n = size_px, limits = obs).numpy()
    # ------
    pdf_pr_jp = _get_pr_pdf(self = 1, qsq_src = Qsq.jpsi, qsq_tgt = qsq)
    pdf_pr_ps = _get_pr_pdf(self = 1, qsq_src = Qsq.psi2, qsq_tgt = qsq)

    jpsi_pr   = pdf_pr_jp.create_sampler(n = size_jx * _RJPSI, limits = obs).numpy()
    psi2_pr   = pdf_pr_ps.create_sampler(n = size_px * _RPSI2, limits = obs).numpy()
    # ------
    datasets  = [jpsi_fr, jpsi_pr, psi2_fr, psi2_pr]

    log.info(f'Sizes for {qsq}:')
    for array in datasets:
        log.info(f'{len(array)}')

    return numpy.concatenate(datasets)
#--------------------------------------
def _get_pr_pdf(self, qsq_src : Qsq, qsq_tgt : Qsq) -> zpdf:
    mu, sg = _get_pr_shape(self = 1, qsq = qsq_src)

    obs = zfit.Space('B_Mass', limits = _OBS_RANGE)
    mu  = zfit.Parameter(f'mu_{qsq_src}_{qsq_tgt}', mu, 4000, 6200)
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
        '_CCbarRatioCalculator__get_target_data',
        _get_target_data)

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

    cfgs  = CCbarRatioCalculatorConf.load(variable = 'none')
    cfg   = cfgs[0]
    block = Block(value = 1)

    cal         = CCbarRatioCalculator(
        cfg     = cfg,
        block   = block,
        project = Project.rk)

    cal.get_ratio(update = True)
#-------------------------------------
