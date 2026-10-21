'''
This module tests the class ToyMaker
'''
import pytest
import mplhep
import matplotlib.pyplot as plt

from typing      import Any
from pathlib     import Path
from zfit.loss   import ExtendedUnbinnedNLL
from fitter      import ToyPlotter
from fitter      import ToyMaker
from fitter      import ToyConf
from dmu.stats   import FitResult
from dmu.stats   import FitParameter
from dmu.stats   import Constraints, Constraint1D, ConstraintND
from dmu.stats   import ConstraintAdder
from dmu.stats   import zfit 
from dmu.testing import get_nll
from dmu.generic import utilities as gut
from dmu.generic import rxran
from dmu         import LogStore

log=LogStore.add_logger('fitter:test_toymaker')
plt.style.use(mplhep.style.LHCb2)
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:gofcalculator', 30)
    LogStore.set_level('dmu:stats:fitter'       , 20)
    LogStore.set_level('fitter:toy_maker'       , 10)
    LogStore.set_level('fitter:constraint_adder', 10)

    with rxran.seed(value = 42),\
         FitParameter.enforce_naming_convention(value = False):
        yield
# ----------------------
def test_simple(
    monkeypatch,
    tmp_path: Path) -> None:
    '''
    Simplest test of ToyMaker
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    log.info('')
    nll   = get_nll(kind='s+b', suffix = '')

    data  = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    cfg   = ToyConf(**data)

    data  = gut.load_data(package='fitter_data', fpath='tests/fits/constraint_adder.yaml')
    cons  = Constraints[Constraint1D | ConstraintND](root = data)

    assert isinstance(nll, ExtendedUnbinnedNLL)
    adr_1d = ConstraintAdder[Constraint1D](nll = nll, constraints = cons.one_dim)
    nll    = adr_1d.get_nll()

    adr_nd = ConstraintAdder[ConstraintND](nll = nll, constraints = cons.multi_dim)
    nll    = adr_nd.get_nll()

    minimizer = zfit.minimize.Minuit()
    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    mkr   = ToyMaker(
        nll=nll, 
        res=FitResult.from_zfit(res), 
        cfg=cfg, 
        cns=cons)
    df    = mkr.get_parameter_information(name = 'test')

    l_col = ['Parameter', 'Value', 'Error', 'Gen', 'Toy', 'GOF', 'Valid', 'Hash']

    assert df.columns.to_list() == l_col

    pars  = nll.get_params()
    assert len(df) == cfg.ntoys * len(pars) 
# ----------------------
@pytest.mark.parametrize('ntoys', [100])
def test_integration(
    monkeypatch,
    tmp_path : Path,
    ntoys    : int | None) -> None:
    '''
    Makes toys and then plots using ToyPlotter

    Parameters 
    -------------
    tmp_path : Where output plots will go
    ntoys    : Number of toys to override what is in config
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    log.info('')
    nll   = get_nll(kind='s+b', suffix = '')
    assert isinstance(nll, ExtendedUnbinnedNLL)

    data = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    cfg  = ToyConf(**data)
    cfg  = cfg.model_copy(update = {'ntoys' : ntoys})

    data : dict[str,Any] = gut.load_data(package='fitter_data', fpath='tests/fits/constraint_adder.yaml') 
    cns  = Constraints[Constraint1D | ConstraintND](root = data)

    adr_1d = ConstraintAdder[Constraint1D](nll = nll, constraints = cns.one_dim)
    nll    = adr_1d.get_nll()

    adr_nd = ConstraintAdder[ConstraintND](nll = nll, constraints = cns.multi_dim)
    nll    = adr_nd.get_nll()

    minimizer = zfit.minimize.Minuit()
    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    mkr = ToyMaker(
        nll=nll, 
        res=FitResult.from_zfit(res), 
        cfg=cfg, 
        cns=cns)
    df  = mkr.get_parameter_information(name = 'nominal')

    cfg = gut.load_conf(package='fitter_data', fpath='tests/toys/toy_plotter_integration.yaml')
    cfg.saving.plt_dir = tmp_path / 'toymaker/integration/plots'
    ptr = ToyPlotter(df=df, cfg=cfg)
    ptr.plot()
# ----------------------
