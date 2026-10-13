'''
Module used to test DataFitter
'''
import pytest

from typing          import Final
from pathlib         import Path
from dmu             import LogStore
from dmu.stats       import FitParameter, zfit
from dmu.stats       import Constraint1D, Constraints
from dmu.stats       import constraint_adder as cad
from dmu.stats       import gof_calculator   as goc
from dmu.generic     import utilities        as gut
from dmu.workflow    import Cache
from dmu.testing     import get_model
from rx_common       import Qsq, Region, Brem, Trigger
from fitter          import DataFitter
from fitter          import ToyMaker
from fitter          import ToyPlotter
from fitter          import ToyConf
from fitter          import FitModelConf
from fitter          import NLLConf

_SEL_CFG : Final[dict] = {
    'default' : {},
    'fit'     : {},
}

_CONSTRAINTS : Final[dict] = {
    'name' : 'mu',
    'kind' : 'GaussianConstraint',
    'mu'   : 5280,
    'sg'   :   10,
}

log=LogStore.add_logger('fitter:test_data_fitter')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:gofcalculator', 30)

    with FitParameter.enforce_naming_convention(value = False):
        yield
# ----------------------
def _rename_model(pdf : zfit.pdf.SumPDF, signal : str, background : str) -> zfit.pdf.SumPDF:
    [sig, bkg] = pdf.pdfs

    sig._name = signal     # type: ignore
    bkg._name = background # type: ignore 

    return pdf
# ----------------------
def test_single_region(tmp_path : Path) -> None:
    '''
    Test fitting with single signal region
    '''
    pdf = get_model(kind='s+b')
    dat = pdf.create_sampler(10_000)
    nll = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)

    cfg_nll = NLLConf(
        nll         = nll, 
        selection   = _SEL_CFG, 
        constraints = [])

    rk_ee_br12  = Region(
        brem    = Brem.brx12,
        trigger = Trigger.rk_ee_os)

    d_nll= {rk_ee_br12 : cfg_nll}
    data = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg  = FitModelConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= Qsq.low,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run(skip_fit = False)
# ----------------------
def test_two_regions(tmp_path : Path) -> None:
    '''
    Test simultaneous fit with two regions
    '''
    obs     = zfit.Space(obs = 'Mass', limits = (4500, 7000)) 

    pdf_001 = get_model(obs=obs, kind='s+b', suffix='001')
    pdf_001 = _rename_model(pdf = pdf_001, signal = 'bpkpee_001', background = 'comb_001')
    dat_001 = pdf_001.create_sampler(10_000)
    nll_001 = zfit.loss.ExtendedUnbinnedNLL(data=dat_001, model=pdf_001)

    pdf_002 = get_model(obs=obs, kind='s+b', suffix='002')
    pdf_002 = _rename_model(pdf = pdf_002, signal = 'bpkpee_002', background = 'comb_002')
    dat_002 = pdf_002.create_sampler(10_000)
    nll_002 = zfit.loss.ExtendedUnbinnedNLL(data=dat_002, model=pdf_002)

    cfg_nll_001 = NLLConf(
        nll         = nll_001, 
        selection   = _SEL_CFG, 
        constraints = [])

    cfg_nll_002 = NLLConf(
        nll         = nll_002, 
        selection   = _SEL_CFG, 
        constraints = [])

    rk_ee_br1   = Region(
        brem    = Brem.one,
        trigger = Trigger.rk_ee_os)

    rk_ee_br2   = Region(
        brem    = Brem.two,
        trigger = Trigger.rk_ee_os)

    d_nll   = {
        rk_ee_br1 : cfg_nll_001,
        rk_ee_br2 : cfg_nll_002,
    }

    q2bin = Qsq.low
    with goc.GofCalculator.disabled(True),\
         Cache.cache_root(path = tmp_path):
        data = gut.load_data(
            package='fitter_data', 
            fpath  ='tests/fits/two_regions.yaml')

        cfg  = FitModelConf(**data)
        cfg  = cfg.specialize(q2bin = q2bin)

        ftr = DataFitter(
            q2bin= q2bin,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run(skip_fit = False)
# ----------------------
def test_two_regions_shared(tmp_path : Path) -> None:
    '''
    Test simultaneous fit with two regions
    '''
    obs     = zfit.Space(obs = 'Mass', limits = (4500, 7000)) 
    nsig    = zfit.param.Parameter('nsig', 0, 0, 1000_000)

    pdf_001 = get_model(obs=obs, kind='s+b', suffix='001', nsig = nsig)
    pdf_001 = _rename_model(pdf = pdf_001, signal = 'bpkpee_001', background = 'comb_001')
    dat_001 = pdf_001.create_sampler(10_000)
    nll_001 = zfit.loss.ExtendedUnbinnedNLL(data=dat_001, model=pdf_001)

    pdf_002 = get_model(obs=obs, kind='s+b', suffix='002', nsig = nsig)
    pdf_002 = _rename_model(pdf = pdf_002, signal = 'bpkpee_002', background = 'comb_002')
    dat_002 = pdf_002.create_sampler(10_000)
    nll_002 = zfit.loss.ExtendedUnbinnedNLL(data=dat_002, model=pdf_002)

    cfg_nll_001 = NLLConf(
        nll         = nll_001, 
        selection   = _SEL_CFG, 
        constraints = [])

    cfg_nll_002 = NLLConf(
        nll         = nll_002, 
        selection   = _SEL_CFG, 
        constraints = [])

    rk_ee_br1   = Region(
        brem    = Brem.one,
        trigger = Trigger.rk_ee_os)

    rk_ee_br2   = Region(
        brem    = Brem.two,
        trigger = Trigger.rk_ee_os)

    d_nll   = {
        rk_ee_br1 : cfg_nll_001,
        rk_ee_br2 : cfg_nll_002,
    }

    q2bin = Qsq.low
    with goc.GofCalculator.disabled(True),\
         Cache.cache_root(path = tmp_path):
        data = gut.load_data(
            package='fitter_data', 
            fpath  ='tests/fits/two_regions.yaml')

        cfg  = FitModelConf(**data)
        cfg  = cfg.specialize(q2bin = q2bin)

        ftr = DataFitter(
            q2bin= q2bin,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run(skip_fit = False)
# ----------------------
def test_with_constraints(tmp_path : Path) -> None:
    '''
    Test fitting with constraints
    '''
    q2bin = Qsq.low
    pdf   = get_model(kind='s+b')
    pdf   = _rename_model(pdf = pdf, signal = 'bpkpee', background = 'comb')
    dat   = pdf.create_sampler(10_000)
    nll   = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)
    cons  = Constraint1D(**_CONSTRAINTS)

    cfg_nll = NLLConf(
        nll         = nll, 
        selection   = _SEL_CFG, 
        constraints = [cons])

    rk_ee_br12  = Region(
        brem    = Brem.brx12,
        trigger = Trigger.rk_ee_os)

    d_nll = {rk_ee_br12 : cfg_nll}

    constraints = Constraints(root = {'mu' : cons})

    adr   = cad.ConstraintAdder(nll=nll, constraints = constraints)
    nll   = adr.get_nll()

    data  = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg   = FitModelConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= q2bin,
            d_nll= d_nll,
            cfg  = cfg)

        ftr.run(skip_fit = False)
# ----------------------
@pytest.mark.parametrize('ntoys', [20])
def test_with_toys(ntoys : int, tmp_path : Path) -> None:
    '''
    Integration test

    - Fitting
    - Making toys
    - Plotting
    '''
    q2bin = Qsq.low
    pdf = get_model(kind='s+b')
    pdf = _rename_model(pdf = pdf, signal = 'bpkpee', background = 'comb')
    dat = pdf.create_sampler(10_000)
    nll = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)

    cfg_nll = NLLConf(
        nll         = nll, 
        selection   = _SEL_CFG, 
        constraints = [])

    rk_ee_br12  = Region(
        brem    = Brem.brx12,
        trigger = Trigger.rk_ee_os)

    d_nll   = {rk_ee_br12 : cfg_nll}
    data    = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg_fit = FitModelConf(**data)

    data    = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    cfg_toy = ToyConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= q2bin,
            d_nll= d_nll,
            cfg  = cfg_fit)
        res = ftr.run(skip_fit = False)

    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        cfg_toy = cfg_toy.model_copy(update = {'ntoys' : ntoys, 'output' : tmp_path / 'toys.parquet'})

        mkr = ToyMaker(
            nll = nll,
            res = res,
            cfg = cfg_toy,
            cns = Constraints.none())
        df  = mkr.get_parameter_information(name = 'nominal')

        cfg = gut.load_conf(package='fitter_data', fpath='tests/toys/toy_plotter_integration.yaml')
        ptr = ToyPlotter(df=df, cfg=cfg)
        ptr.plot()
# ----------------------
