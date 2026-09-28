'''
This module contains tests for the ConstraintAdder class
'''

import math
import tqdm
import pandas as pnd
import pytest

from dmu         import LogStore
from dmu.stats   import zfit
from dmu.stats   import Constraint1D, ConstraintND, Constraints
from dmu.stats   import ConstraintAdder
from dmu.stats   import print_constraints
from dmu.generic import utilities as gut
from dmu.generic import rxran
from dmu.testing import get_nll

from zfit.data   import SamplerData
from zfit.loss   import ExtendedUnbinnedNLL, UnbinnedNLL 

log             = LogStore.add_logger('dmu:stats:test_constraint_adder')
type Loss       = ExtendedUnbinnedNLL | UnbinnedNLL
type Constraint = Constraint1D        | ConstraintND
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:constraint_adder'     , 10)
    LogStore.set_level('dmu:stats:test_constraint_adder', 10)

    with rxran.seed(42):
        yield
# ----------------------
def _extract_parameters(nll : Loss) -> pnd.DataFrame:
    '''
    Parameters
    -------------
    nll : Likelihood, with constraints

    Returns
    -------------
    Pandas series with observed value and parameter name
    '''
    data  = {'Parameter' : [], 'Value' : []}
    s_par = nll.get_params()
    for par in s_par:
        value = float(par.value().numpy())
        data['Parameter'].append(par.name)
        data['Value'    ].append(value)

    df = pnd.DataFrame(data)

    return df
# ----------------------
def _validate(
    df   : pnd.DataFrame, 
    cons : Constraints[Constraint1D]) -> None:
    '''
    Check that for each parameter the mean and std from the dataframe (toys)
    is compatible (within 15%) to what is in the config

    Parameters
    -------------
    df : Dataframe with parameter name, observed value and toy inde
    cfg: Config with user defined information 
    '''
    for toy_par, df_par in df.groupby('Parameter'):
        if toy_par not in cons.root:
            continue

        cfg_block = cons.root[toy_par]
        log.debug('')
        log.debug(f'Parameter: {toy_par}')

        tmp  = df_par['Value'].mean()
        mean = float(tmp)
        expc = cfg_block.mu

        log.debug(f'Mean: {mean:.2f}/{expc:.2f}')
        assert math.isclose(mean, expc, rel_tol=0.01) # Constrain and measurement should be the same

        if   cfg_block.kind == 'GaussianConstraint':
            expc = cfg_block.sg
        elif cfg_block.kind == 'PoissonConstraint':
            expc = math.sqrt(cfg_block.mu)
        else:
            raise ValueError(f'Invalid constraint: {cfg_block.kind}')

        tmp  = df_par['Value'].std()
        std  = float(tmp)

        log.debug(f'STD : {std:.2f}/{expc:.2f}')
        assert std < expc # Parameters distribution in data should be narrower than constrain
# ----------------------
def test_uncorrelated() -> None:
    '''
    Test multiple uncorrelated constraints
    '''
    nll  = get_nll(kind='s+b', suffix = '')
    data = gut.load_data(package='dmu_data', fpath='tests/stats/constraints/uncorrelated.yaml')
    cons = Constraints[Constraint1D](root = data)

    cad = ConstraintAdder(nll=nll, constraints=cons)
    nll = cad.get_nll()
# ----------------------
def test_correlated() -> None:
    '''
    Test constraints of correlated parameters
    '''
    nll = get_nll(kind='s+b', suffix = '')
    data = gut.load_data(package='dmu_data', fpath='tests/stats/constraints/correlated.yaml')
    cons = Constraints[ConstraintND](root = data)

    cad = ConstraintAdder(nll=nll, constraints=cons)
    nll = cad.get_nll()
# ----------------------
@pytest.mark.timeout(100)
def test_toy() -> None:
    '''
    Tests toy constraint addition in a loop
    with timeout extended in order to profile
    '''
    ntoy= 100
    nll = get_nll(kind='s+b', suffix = '', nentries = 2000) # Do not change 2000, constraints are for 2000

    data = gut.load_data(package='dmu_data', fpath='tests/stats/constraints/uncorrelated.yaml')
    cons = Constraints[Constraint1D](root = data)

    log.info('')
    print_constraints(cons)

    mnm = zfit.minimize.Minuit()
    cad = ConstraintAdder(nll=nll, constraints=cons)
    nll = cad.get_nll()

    l_df : list[pnd.DataFrame] = []
    sam = nll.data[0]
    if not isinstance(sam, SamplerData):
        raise ValueError('Data is not in a sampler')

    for _ in tqdm.trange(ntoy, ascii=' -'):
        for constraint in cons.root.values():
            constraint.resample()

        sam.resample()
        mnm.minimize(nll)

        df = _extract_parameters(nll=nll)
        l_df.append(df)

    df = pnd.concat(l_df, ignore_index=True)

    _validate(df=df, cons=cons)
# ----------------------
