'''
Module with tests for CCbarRatioCalculator class
'''
import pytest
import numpy

from typing      import Final
from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import zfit
from dmu.generic import utilities as gut
from rx_common   import Block, Channel, Component, Project, Qsq
from hqm.config  import CCbarRatioCalculatorConf
from hqm.ratc    import CCbarRatioCalculator
from hqm.plotter import Plotter
from hqm.trfc    import TransferFunction

zpdf = zfit.pdf.BasePDF

_MASS_RANGE : Final[tuple[float,float]] = 4500, 6000
_TRAN_RANGE : Final[tuple[float,float]] = -500,  500

# Part reco / Fully reco
_RJPSI : Final[float] = 0.5
_RPSI2 : Final[float] = 0.5
_SIZE_FULL : Final[int] = 20_000

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
        return 10_000

    if qsq_src == Qsq.jpsi and qsq_tgt == Qsq.psi2:
        return  2_000

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.jpsi:
        return  1_000

    if qsq_src == Qsq.psi2 and qsq_tgt == Qsq.psi2:
        return  2_000

    raise ValueError('Invalid q2')
#-------------------------------------
def _get_peak(self, comp : Component, qsq : Qsq) -> tuple[float,float]:
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
def _get_source_data(self, qsq : Qsq) -> numpy.ndarray:
    gaus = numpy.random.normal(0, 50, size = _SIZE_FULL)

    if qsq == Qsq.jpsi:
        return numpy.random.uniform(3700, 5100, size = _SIZE_FULL) + gaus

    if qsq == Qsq.psi2:
        return numpy.random.uniform(3900, 4900, size = _SIZE_FULL) + gaus

    raise ValueError(f'Invalid q2 bin: {qsq}')
#--------------------------------------
def _get_pr(qsq_src : Qsq, qsq_tgt : Qsq, frac : float) -> numpy.ndarray:
    arr_src = _get_source_data(self = 1, qsq = qsq_src)
    dmu, sg = _get_mu_sg(qsq_src = qsq_src, qsq_tgt = qsq_tgt)
    arr_smr = numpy.random.normal(dmu, sg, len(arr_src))
    arr_tgt = arr_src + arr_smr

    size    = _get_fr_entries(qsq_src = qsq_src, qsq_tgt = qsq_tgt)
    new_size= int(size * frac)
    arr_flt = numpy.random.choice(arr_tgt, size = new_size, replace = True)

    return arr_flt
#--------------------------------------
def _get_target_data(self, qsq : Qsq) -> numpy.ndarray:
    mu_jj, sg_jj = _get_peak(self = 1, comp=Component.bpkpjpsiee, qsq=Qsq.jpsi)
    mu_jp, sg_jp = _get_peak(self = 1, comp=Component.bpkpjpsiee, qsq=Qsq.psi2)

    mu_pj, sg_pj = _get_peak(self = 1, comp=Component.bpkppsi2ee, qsq=Qsq.jpsi)
    mu_pp, sg_pp = _get_peak(self = 1, comp=Component.bpkppsi2ee, qsq=Qsq.psi2)

    size_jx = _get_fr_entries(qsq_src=Qsq.jpsi, qsq_tgt=qsq)
    size_px = _get_fr_entries(qsq_src=Qsq.psi2, qsq_tgt=qsq)

    if   qsq == Qsq.jpsi:
        jpsi_fr = numpy.random.normal(mu_jj, sg_jj, size = size_jx)
        psi2_fr = numpy.random.normal(mu_pj, sg_pj, size = size_px)

        jpsi_pr = _get_pr(qsq_src = Qsq.jpsi, qsq_tgt = qsq, frac = _RJPSI)
        psi2_pr = _get_pr(qsq_src = Qsq.psi2, qsq_tgt = qsq, frac = _RPSI2)
    elif qsq == Qsq.psi2:
        psi2_fr = numpy.random.normal(mu_pp, sg_pp, size = size_jx)
        jpsi_fr = numpy.random.normal(mu_jp, sg_jp, size = size_px)

        jpsi_pr = _get_pr(qsq_src = Qsq.jpsi, qsq_tgt = qsq, frac = _RJPSI)
        psi2_pr = _get_pr(qsq_src = Qsq.psi2, qsq_tgt = qsq, frac = _RPSI2)
    else:
        raise ValueError(f'Invalid q2 bin: {qsq}')

    datasets = [jpsi_fr, psi2_fr, jpsi_pr, psi2_pr]

    return numpy.concatenate(datasets)
#--------------------------------------
def _get_trfc(self, qsq_src : Qsq, qsq_tgt : Qsq) -> TransferFunction:
    data = gut.load_data(
        package = 'hqm_data', 
        fpath   =f'tests/trfc_{qsq_src}_{qsq_tgt}.json')

    return TransferFunction(**data)
#--------------------------------------
def _get_mc_pdf(self, comp : Component, qsq : Qsq, channel : Channel) -> zpdf:
    mu, sg = _get_peak(self = 1, comp = comp, qsq = qsq)

    obs = zfit.Space('B_Mass', limits = (3000, 7000))
    nrm = zfit.Space('B_Mass', limits = (4500, 7000))
    mu  = zfit.Parameter(f'mu_{comp}_{qsq}', mu, 4800, 6200)
    sg  = zfit.Parameter(f'sg_{comp}_{qsq}', sg,    0, 300)

    mu.floating = False
    sg.floating = False

    pdf = zfit.pdf.Gauss(
        name  = comp,
        mu    = mu, 
        sigma = sg, 
        obs   = obs, 
        norm  = nrm)

    return pdf
#--------------------------------------
@pytest.fixture(autouse = True)
def _use_fake_masses(monkeypatch):
    monkeypatch.setattr(
        CCbarRatioCalculator,
        '_CCbarRatioCalculator__get_source_data',
        _get_source_data)

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
        '_CCbarRatioCalculator__get_trfc',
        _get_trfc)
#-------------------------------------
def test_unbinned(monkeypatch, tmp_path : Path):
    '''
    Test in unbinned case
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    cfgs  = CCbarRatioCalculatorConf.load(variable = 'none')
    cfg   = cfgs[0]
    block = Block(value = 1)

    with Plotter.plot(path = tmp_path / 'plots'):
        cal         = CCbarRatioCalculator(
            cfg     = cfg,
            block   = block, 
            project = Project.rk)

        ratio = cal.get_ratio()
#-------------------------------------
