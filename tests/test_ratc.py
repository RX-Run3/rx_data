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
from rx_common   import Block, Component, Project, Qsq
from hqm.config  import CCbarRatioCalculatorConf
from hqm.ratc    import CCbarRatioCalculator
from hqm.plotter import Plotter
from hqm.trfc    import TransferFunction

zpdf = zfit.pdf.BasePDF

_MASS_RANGE : Final[tuple[float,float]] = 4500, 6000
_TRAN_RANGE : Final[tuple[float,float]] = -500,  500

log=LogStore.add_logger('hqm:test_ratc')

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
        mu = 5100
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
def set_logs():
    LogStore.set_level('scripts:zutils/utils'    , 30)
    LogStore.set_level('rx_hqm2:data_store'      , 30)
    LogStore.set_level('rx_scripts:storage/cache', 30)
    LogStore.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    LogStore.set_level('tools:calc_utility'      , 40)
#--------------------------------------
def _get_source_data(self, qsq : Qsq) -> numpy.ndarray:
    if qsq == Qsq.jpsi:
        return numpy.random.uniform(3700, 5100, size = 10_000)

    if qsq == Qsq.psi2:
        return numpy.random.uniform(3500, 4900, size = 10_000)

    raise ValueError(f'Invalid q2 bin: {qsq}')
#--------------------------------------
def _get_pr(qsq_src : Qsq, qsq_tgt : Qsq) -> numpy.ndarray:
    arr_src = _get_source_data(self = 1, qsq = qsq_src)
    if qsq_src != qsq_tgt:
        size    = 0.2 * len(arr_src)
        arr_src = numpy.random.choice(arr_src, size = int(size), replace = False)

    dmu, sg = _get_mu_sg(qsq_src = qsq_src, qsq_tgt = qsq_tgt)

    return arr_src + numpy.random.normal(dmu, sg, len(arr_src))
#--------------------------------------
def _get_target_data(self, qsq : Qsq) -> numpy.ndarray:
    mu_jj, sg_jj = _get_peak(self = 1, comp=Component.bpkpjpsiee, qsq=Qsq.jpsi)
    mu_jp, sg_jp = _get_peak(self = 1, comp=Component.bpkpjpsiee, qsq=Qsq.psi2)

    mu_pj, sg_pj = _get_peak(self = 1, comp=Component.bpkppsi2ee, qsq=Qsq.jpsi)
    mu_pp, sg_pp = _get_peak(self = 1, comp=Component.bpkppsi2ee, qsq=Qsq.psi2)

    if   qsq == Qsq.jpsi:
        jpsi_fr = numpy.random.normal(mu_jj, sg_jj, size = 10_000)
        psi2_fr = numpy.random.normal(mu_pj, sg_pj, size =  1_000)

        jpsi_pr = _get_pr(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        psi2_pr = _get_pr(qsq_src = Qsq.psi2, qsq_tgt = qsq)
    elif qsq == Qsq.psi2:
        psi2_fr = numpy.random.normal(mu_pp, sg_pp, size = 5_000)
        jpsi_fr = numpy.random.normal(mu_jp, sg_jp, size = 3_000)

        jpsi_pr = _get_pr(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        psi2_pr = _get_pr(qsq_src = Qsq.psi2, qsq_tgt = qsq)
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
def _get_mc_pdf(self, comp : Component, qsq : Qsq) -> zpdf:
    mu, sg = _get_peak(self = 1, comp = comp, qsq = qsq)

    obs = zfit.Space('B_Mass', limits = (4500, 6000))
    mu  = zfit.Parameter(f'mu_{comp}_{qsq}', mu, 4800, 6200)
    sg  = zfit.Parameter(f'sg_{comp}_{qsq}', sg,    0, 300)

    mu.floating = False
    sg.floating = False

    return zfit.pdf.Gauss(mu = mu, sigma = sg, obs = obs)
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
