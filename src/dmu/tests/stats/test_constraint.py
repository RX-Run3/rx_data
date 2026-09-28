'''
Module with tests for classes and functions in constraint.py module
'''
import numpy
import pytest

from pathlib         import Path
from typing          import Final
from dmu             import LogStore
from dmu.generic     import utilities          as gut
from dmu.stats       import Constraint1D 
from dmu.stats       import ConstraintND
from dmu.stats       import Constraint
from dmu.stats       import print_constraints 
from dmu.stats       import zfit
from zfit            import Parameter          as zpar
from zfit.constraint import GaussianConstraint as GConstraint 
from zfit.constraint import PoissonConstraint  as PConstraint 

log = LogStore.add_logger('dmu:test_constraint')
# ----------------------
_EXPECTED_MU : Final[list[float]] = [
    5199.89615,
    149.79230,
    1001.32,
    1001.32,
]
_EXPECTED_SG : Final[list[float]] = [
    0.9036161,
    1.807232353289259,
    31.62811407592934,
    31.62811407592934,
]
# ---------------------------------
def _load_constraints(kind = 'uncorrelated') -> list[dict]:
    '''
    Parameters
    -------------
    kind: Type of constraints

    Returns
    -------------
    List of dictionary with information
    '''
    raw_input : dict[str,dict] = gut.load_data(package='dmu_data', fpath=f'tests/stats/constraints/{kind}.yaml')

    data : list[dict] = [] 
    for name, entry in raw_input.items():
        entry['name'] = name
        data.append(entry)

    return data
# ---------------------------------
class ParsHolder:
    '''
    Class representing object holding parameters
    '''
    # ------------
    def get_params(self) -> set[zpar]:
        '''
        Returns set of parameters
        '''
        mu   = zfit.Parameter('mu', 5300, 5000, 6000)
        sg   = zfit.Parameter('sg',   20,   10,   60)

        nsig = zfit.Parameter('nsig', 1000, 500, 2000)
        nbkg = zfit.Parameter('nbkg', 1000, 500, 2000)

        return {mu, sg, nsig, nbkg}
# ---------------------------------
@pytest.mark.parametrize('data, mean, stdv', zip(_load_constraints(), _EXPECTED_MU, _EXPECTED_SG, strict = True))
def test_constraint1D(data : dict, mean : float, stdv : float):
    '''
    Basic test for Constraint1D 
    '''
    numpy.random.seed(42)
    holder = ParsHolder()
    cons   = Constraint1D(**data)

    zcons  = cons.zfit_cons(holder)
    assert isinstance(zcons, (GConstraint, PConstraint))

    values = []
    for _ in range(100):
        cons.resample()
        val = cons.observation.value()
        values.append(val)

    mean_test = numpy.mean(values)
    stdv_test = numpy.std(values)

    assert numpy.isclose(mean, mean_test, rtol=1e-5)
    assert numpy.isclose(stdv, stdv_test, rtol=1e-5)
# ---------------------------------
def test_print_1d():
    '''
    Test printing of constraints
    '''
    numpy.random.seed(42)
    l_cons : list[Constraint] = [ Constraint1D(**data) for data in _load_constraints() ]

    log.info('')
    print_constraints(l_cons)
# ---------------------------------
def test_print_nd():
    '''
    Test printing of constraints
    '''
    numpy.random.seed(42)
    l_cons : list[Constraint] = [ ConstraintND(**data) for data in _load_constraints(kind = 'correlated') ]

    log.info('')
    print_constraints(l_cons)
# ---------------------------------
def test_constraintND():
    numpy.random.seed(42)

    data = gut.load_data(package='dmu_data', fpath='tests/stats/constraints/correlated.yaml')
    block= data['signal_shape']

    holder = ParsHolder()
    cons   = ConstraintND(**block)
    zcons  = cons.zfit_cons(holder)

    assert isinstance(zcons, GConstraint)

    l_mu = []
    l_sg = []
    for _ in range(1000):
        cons.resample()
        mu = cons.observation('mu')
        sg = cons.observation('sg')

        l_mu.append(mu)
        l_sg.append(sg)

    mean_mu = numpy.mean(l_mu)
    mean_sg = numpy.mean(l_sg)
    stdv_mu = numpy.std(l_mu)
    stdv_sg = numpy.std(l_sg)

    assert numpy.isclose(mean_mu , 5199.658, rtol=1e-5)
    assert numpy.isclose(stdv_mu , 9.611858, rtol=1e-5)
    assert numpy.isclose(mean_sg , 150.0634, rtol=1e-5)
    assert numpy.isclose(stdv_sg , 1.998920, rtol=1e-5)
# ---------------------------------
def test_from_dict():
    '''
    Test method making constraints from dictionary
    '''
    data = {
        'a' : (1., 1.),
        'b' : (3., 2.),
    }

    constraints = Constraint1D.from_dict(data = data, kind = 'GaussianConstraint')
    assert constraints
    assert isinstance(constraints, list)
    assert all( isinstance(const, Constraint1D) for const in constraints )

    print_constraints(constraints)
# ---------------------------------
def test_serialization_nd(tmp_path : Path):
    '''
    Tests serialization to and from JSON
    fro ND constraints
    '''
    data = _load_constraints(kind = 'correlated')[0]
    obj  = ConstraintND(**data)

    path = tmp_path / 'ND.json'
    obj.to_json(path = path)

    assert path.exists()

    res = ConstraintND.from_json(path=path)

    assert res == obj
# ---------------------------------
@pytest.mark.parametrize('data', _load_constraints(kind = 'uncorrelated'))
def test_serialization_1d(tmp_path : Path, data):
    '''
    Tests serialization to and from JSON
    fro ND constraints
    '''
    obj  = Constraint1D(**data)

    path = tmp_path / '1D.json'
    obj.to_json(path = path)

    assert path.exists()

    res = Constraint1D.from_json(path=path)

    assert res == obj
