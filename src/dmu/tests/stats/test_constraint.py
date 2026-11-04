'''
Module with tests for classes and functions in constraint.py module
'''
import numpy
import pytest

from collections.abc import Sequence
from pathlib         import Path
from typing          import overload
from typing          import Literal
from typing          import Final
from dmu             import LogStore
from dmu.stats       import ConstraintType
from dmu.stats       import Constraint1D
from dmu.stats       import ConstraintND
from dmu.stats       import Constraints
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
# ----------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    numpy.random.seed(42)
# ---------------------------------
@overload
def _load_constraints(kind : Literal['uncorrelated']) -> Sequence[Constraint1D]:...
@overload
def _load_constraints(kind : Literal['correlated'  ]) -> Sequence[ConstraintND]:...
def _load_constraints(kind : Literal['correlated', 'uncorrelated']) -> Sequence[Constraint1D | ConstraintND]:
    '''
    Parameters
    -------------
    kind: Type of constraints

    Returns
    -------------
    List holding constraints
    '''
    cons = Constraints.from_package(package = 'dmu_data', loc = f'tests/stats/constraints/{kind}.yaml')

    return list(cons.root.values())
# ---------------------------------
class ParsHolder:
    '''
    Class representing object holding parameters
    '''
    # ------------
    def get_params(self, floating : bool) -> set[zpar]:
        '''
        Returns set of parameters
        '''
        _    = floating
        if not floating:
            return set()

        mu   = zfit.Parameter('mu', 5300, 5000, 6000)
        sg   = zfit.Parameter('sg',   20,   10,   60)

        nsig = zfit.Parameter('nsig', 1000, 500, 2000)
        nbkg = zfit.Parameter('nbkg', 1000, 500, 2000)

        return {mu, sg, nsig, nbkg}
# ---------------------------------
@pytest.mark.parametrize('cons, mean, stdv', zip(_load_constraints('uncorrelated'), _EXPECTED_MU, _EXPECTED_SG, strict = True))
def test_constraint1D(cons : Constraint1D, mean : float, stdv : float):
    '''
    Basic test for Constraint1D
    '''
    holder = ParsHolder()
    zcons  = cons.zfit_cons(holder = holder)

    assert isinstance(zcons, (GConstraint, PConstraint))

    values : list[float] = []
    for _ in range(100):
        cons.resample()
        values.append(cons.current_observation)

    mean_test = numpy.mean(values)
    stdv_test = numpy.std(values)

    assert numpy.isclose(mean, mean_test, rtol=1e-5)
    assert numpy.isclose(stdv, stdv_test, rtol=1e-5)
# ---------------------------------
def test_print_1d():
    '''
    Test printing of constraints
    '''
    cons = Constraints[Constraint1D].from_package(
        package = 'dmu_data',
        loc     = 'tests/stats/constraints/uncorrelated.yaml')

    log.info(f'\n{cons}')

    mu_cons = cons.root['mu']
    with pytest.raises(ValueError):
        mu_cons.observation(name = 'fake')

    assert mu_cons.observation(name = 'fake', raise_on_missing=False) is None
# ---------------------------------
def test_print_nd():
    '''
    Test printing of constraints
    '''
    cons = Constraints[ConstraintND].from_package(
        package = 'dmu_data',
        loc     = 'tests/stats/constraints/correlated.yaml')

    log.info(f'\n{cons}')

    sig_cons = cons.root['signal_shape']
    with pytest.raises(ValueError):
        sig_cons.observation(name = 'fake')

    assert sig_cons.observation(name = 'fake', raise_on_missing=False) is None
# ---------------------------------
def test_mixed():
    '''
    Mix 1D and ND constraints
    '''
    cn1d = Constraints[Constraint1D].from_package(
        package='dmu_data', loc = 'tests/stats/constraints/uncorrelated_gauss.yaml')

    cnnd = Constraints[ConstraintND].from_package(
        package='dmu_data', loc = 'tests/stats/constraints/correlated.yaml')

    root = {**cn1d.root, **cnnd.root}
    cons = Constraints(root = root)
    log.info(f'\n{cons}')

    merged = cons.merge(name = 'merged')
    log.info(f'\n{merged}')
# ---------------------------------
def test_constraintND():
    '''
    Test ND constraints, loading and resampling
    '''
    obj    = _load_constraints(kind = 'correlated')[0]
    data   = obj.model_dump()

    holder = ParsHolder()
    cons   = ConstraintND(**data)
    zcons  = cons.zfit_cons(holder)

    assert isinstance(zcons, GConstraint)

    l_mu : list[float] = []
    l_sg : list[float] = []
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

    constraints = Constraint1D.from_dict(data = data, kind = ConstraintType.gauss)
    assert constraints.root
    assert all( isinstance(const, Constraint1D) for const in constraints.root.values() )

    log.info(f'\n{constraints}')
# ---------------------------------
def test_serialization_nd(tmp_path : Path):
    '''
    Tests serialization to and from JSON
    fro ND constraints
    '''
    obj  = _load_constraints(kind = 'correlated')[0]

    path = tmp_path / 'ND.json'
    obj.to_json(path = path)

    assert path.exists()

    res = ConstraintND.from_json(path=path)

    assert res == obj
# ---------------------------------
@pytest.mark.parametrize('obj', _load_constraints(kind = 'uncorrelated'))
def test_serialization_1d(tmp_path : Path, obj : Constraint1D):
    '''
    Tests serialization to and from JSON
    fro ND constraints
    '''
    path = tmp_path / '1D.json'
    obj.to_json(path = path)

    assert path.exists()

    res = Constraint1D.from_json(path=path)

    assert res == obj
# ---------------------------------
def test_serialize_constraints(tmp_path : Path):
    '''
    Test that container of constraints can be serialized
    '''
    cn1d = Constraints[Constraint1D].from_package(package='dmu_data', loc ='tests/stats/constraints/uncorrelated_gauss.yaml')
    cnnd = Constraints[ConstraintND].from_package(package='dmu_data', loc ='tests/stats/constraints/correlated.yaml')

    root = {**cn1d.root, **cnnd.root}
    cons = Constraints[Constraint1D | ConstraintND](root = root)

    json_path = tmp_path / 'constraints.json'
    cons.to_json(json_path)

    loaded = Constraints[Constraint1D | ConstraintND].from_json(json_path)

    assert loaded == cons
# ---------------------------------
