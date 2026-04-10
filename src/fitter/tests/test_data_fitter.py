'''
Module used to test DataFitter
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import pytest

from typing          import Final
from pathlib         import Path
from dmu             import LogStore
from dmu.stats       import FitParameter, zfit
from dmu.stats       import Constraint1D
from dmu.stats       import constraint_adder as cad
from dmu.stats       import gof_calculator   as goc
from dmu.generic     import utilities        as gut
from dmu.workflow    import Cache
from dmu.testing     import get_model
from rx_common       import Qsq, Region
from fitter          import DataFitter
from fitter          import ToyMaker
from fitter          import ToyPlotter
from fitter          import ToyConf
from fitter          import FitModelConf

_SEL_CFG : Final[dict] = {
    'selection' : {'default' : {}, 'fit' : {}}
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
def test_single_region(tmp_path : Path) -> None:
    '''
    Test fitting with single signal region
    '''
    pdf = get_model(kind='s+b')
    dat = pdf.create_sampler(10_000)
    nll = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)

    d_nll= {Region.region_001 : (nll, _SEL_CFG)}
    data = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg  = FitModelConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= Qsq.jpsi,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run()
# ----------------------
def test_two_regions(tmp_path : Path) -> None:
    '''
    Test simultaneous fit with two regions
    '''
    obs     = None

    pdf_001 = get_model(obs=obs, kind='s+b', suffix='001')
    dat_001 = pdf_001.create_sampler(10_000)
    nll_001 = zfit.loss.ExtendedUnbinnedNLL(data=dat_001, model=pdf_001)

    pdf_002 = get_model(obs=obs, kind='s+b', suffix='002')
    dat_002 = pdf_002.create_sampler(10_000)
    nll_002 = zfit.loss.ExtendedUnbinnedNLL(data=dat_002, model=pdf_002)

    d_nll   = {
        Region.region_001 : (nll_001, _SEL_CFG),
        Region.region_002 : (nll_002, _SEL_CFG),
    }

    with goc.GofCalculator.disabled(True),\
         Cache.cache_root(path = tmp_path):
        data = gut.load_data(package='fitter_data', fpath='tests/fits/two_regions.yaml')
        cfg  = FitModelConf(**data)

        ftr = DataFitter(
            q2bin= Qsq.jpsi,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run()
# ----------------------
def test_two_regions_common_pars(tmp_path : Path) -> None:
    '''
    Test simultaneous fit with two regions
    and common parameters
    '''
    nsig    = zfit.param.Parameter('nsig', 0, 0, 1000_000)
    obs     = None

    pdf_001 = get_model(obs=obs, kind='signal', suffix='001')
    pdf_001 = pdf_001.create_extended(yield_ = nsig)
    dat_001 = pdf_001.create_sampler(10_000)
    nll_001 = zfit.loss.ExtendedUnbinnedNLL(data=dat_001, model=pdf_001)

    pdf_002 = get_model(obs=obs, kind='signal', suffix='002')
    pdf_002 = pdf_002.create_extended(yield_ = nsig)
    dat_002 = pdf_002.create_sampler(10_000)
    nll_002 = zfit.loss.ExtendedUnbinnedNLL(data=dat_002, model=pdf_002)

    d_nll   = {
        Region.region_001 : (nll_001, _SEL_CFG),
        Region.region_002 : (nll_002, _SEL_CFG),
    }

    with goc.GofCalculator.disabled(True),\
         Cache.cache_root(path = tmp_path):
        data = gut.load_data(package='fitter_data', fpath='tests/fits/two_regions.yaml')
        cfg  = FitModelConf(**data)

        ftr = DataFitter(
            q2bin= Qsq.jpsi,
            d_nll= d_nll,
            cfg  = cfg)
        ftr.run()
# ----------------------
def test_with_constraints(tmp_path : Path) -> None:
    '''
    Test fitting with constraints
    '''
    pdf   = get_model(kind='s+b')
    dat   = pdf.create_sampler(10_000)
    nll   = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)

    d_nll = {Region.region_001 : (nll, _SEL_CFG)}
    cons  = Constraint1D(**_CONSTRAINTS)

    adr   = cad.ConstraintAdder(nll=nll, constraints = [cons])
    nll   = adr.get_nll()

    data  = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg   = FitModelConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= Qsq.jpsi,
            d_nll= d_nll,
            cfg  = cfg)

        ftr.run()
# ----------------------
@pytest.mark.parametrize('ntoys', [20])
def test_with_toys(ntoys : int, tmp_path : Path) -> None:
    '''
    Integration test

    - Fitting
    - Making toys
    - Plotting
    '''
    pdf = get_model(kind='s+b')
    dat = pdf.create_sampler(10_000)
    nll = zfit.loss.ExtendedUnbinnedNLL(data=dat, model=pdf)

    d_nll   = {Region.region_001 : (nll, _SEL_CFG)}

    data    = gut.load_data(package='fitter_data', fpath='tests/fits/single_region.yaml')
    cfg_fit = FitModelConf(**data)

    data    = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    cfg_toy = ToyConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = DataFitter(
            q2bin= Qsq.jpsi,
            d_nll= d_nll,
            cfg  = cfg_fit)
        res = ftr.run()

    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        cfg_toy = cfg_toy.model_copy(update = {'ntoys' : ntoys, 'output' : tmp_path / 'toys.parquet'})

        mkr = ToyMaker(
            nll = nll,
            res = res,
            cfg = cfg_toy,
            cns = [])
        df  = mkr.get_parameter_information(name = 'nominal')

        cfg = gut.load_conf(package='fitter_data', fpath='tests/toys/toy_plotter_integration.yaml')
        ptr = ToyPlotter(df=df, cfg=cfg)
        ptr.plot()
# ----------------------
