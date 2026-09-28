'''
Module containing constraint classes 
'''

import yaml
import json
import math
import numpy
import pprint

from collections.abc import Mapping
from pathlib         import Path
from typing          import Literal, Self, Sequence
from tabulate        import tabulate
from functools       import cached_property
from zfit.constraint import GaussianConstraint as GConstraint
from zfit.constraint import PoissonConstraint  as PConstraint
from zfit.param      import Parameter as zpar
from pydantic        import BaseModel, model_validator, TypeAdapter
from pydantic        import RootModel

from dmu             import LogStore
from .fit_result     import FitResult
from .protocols      import ParsHolder
from .types          import ConstraintType
from .imports        import zfit

log   = LogStore.add_logger('dmu:stats:constraint')
# ----------------------------------------
class Constraint(BaseModel):
    '''
    Class with common code to 1D and ND constraints
    '''
    name : str
    # ----------------------
    def calibrate(self, result : FitResult) -> 'Constraint':
        _ = result

        raise NotImplementedError('Cannot calibrate base Constraint')
    # ----------------------
    def resample(self) -> None:
        raise NotImplementedError('Cannot resample base Constraint')
    # ----------------------
    def zfit_cons(self, holder : ParsHolder) -> GConstraint | PConstraint:
        _ = holder

        raise NotImplementedError('Cannot extract zfit constraint from base Constraint')
    # ----------------------
    def string(self, kind : Literal['yaml', 'json']) -> str:
        '''
        Parameters
        ---------------
        kind: Type of formatting, e.g. yaml, json

        Returns
        ---------------
        String version
        '''
        data = self.model_dump_json(indent = 2)
        if kind == 'json':
            return data

        return yaml.dump(json.loads(data), indent = 2)
    # ----------------------
    @classmethod
    def from_json(cls, path : Path) -> Self:
        '''
        Parameters
        -------------
        path: Path to JSON file to load constraint

        Returns
        -------------
        Constraint
        '''
        if not path.exists():
            raise ValueError(f'Path not found: {path}')

        with open(path) as ifile:
            data = json.load(ifile)

        return cls(**data)
    # ----------------------
    def to_json(self, path : Path) -> None:
        '''
        Parameters
        -------------
        path: Path to JSON file that will store 
        '''
        data = self.model_dump_json(indent=2)

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as ofile:
            ofile.write(data)
    # ----------------------
    def __lt__(self, other : 'Constraint1D') -> bool:
        '''
        Sort constraints by name
        '''
        return self.name < other.name
# ----------------------------------------
class ConstraintND(Constraint):
    '''
    Class meant to symbolize NDimensional Gaussian constraint
    '''
    kind       : ConstraintType 
    parameters : list[str]
    values     : list[float]
    cov        : list[list[float]]
    # ----------------------
    @property
    def errors(self) -> list[float]:
        '''
        List of errors
        '''
        npar      = len(self.parameters)
        variables = [ self.cov[ipar][ipar] for ipar in range(npar) ]

        return [ math.sqrt(var) for var in variables ]
    # ----------------------
    def calibrate(self, result : FitResult) -> 'ConstraintND':
        '''
        Re-centers mu values of this constraint to value of parameter in holder.
        Needed before fitting toys. The constraints need to be consistent with the
        parameter values used to generate toy data.

        Parameters
        -------------
        result: Object holding result of fit

        Returns
        -------------
        Copy of this constraint with means calibrated
        '''
        new_values : list[float] = []

        for name, old_value in zip(self.parameters, self.values, strict = True):
            new_value, _ = result[name]
            new_values.append(new_value)

            log.info(f'{name:<20}{old_value:<20.3f}{"--->":<20}{new_value:<20.3f}')

        return ConstraintND(
            name       = self.name,
            kind       = self.kind,
            parameters = self.parameters,
            values     = new_values, 
            cov        = self.cov,
        )
    # ----------------------
    def __str__(self) -> str:
        '''
        Returns
        -------------
        String representation of constrint
        '''
        parameters = [ f'{name:<50}{value:<20.3f}' for name, value in zip(self.parameters, self.values, strict = True) ]

        msg  = '\n'
        msg += '\n'
        msg += 'Covariance:\n'
        msg += tabulate(self.cov, tablefmt="grid") + '\n'
        msg += '\n'
        msg += 'Parameters\n'
        msg += '---------------\n'
        msg += '\n'.join(parameters)
        
        return msg
    # ---------------------
    @model_validator(mode='after')
    def check_dimensions(self) -> 'ConstraintND':
        '''
        Checks that all the inputs are of the same dimension
        '''
        dimension = len(self.parameters)
        
        if len(self.values) != dimension:
            raise ValueError(f"observation length ({len(self.values)}) must match parameters length ({dimension})")
        
        if len(self.cov) != dimension:
            raise ValueError(f"cov must have {dimension} rows, but has {len(self.cov)}")
            
        for irow, row in enumerate(self.cov):
            if len(row) != dimension:
                raise ValueError(f"cov row {irow} must have {dimension} columns, but has {len(row)}")
        
        return self
    # ----------------------
    def _obs_from_holder(self, holder : ParsHolder) -> list[zpar]:
        '''
        Parameters
        ------------------
        holder: Object holding parameters

        Returns
        ------------------
        Observables of constraint, i.e. parameters to constrain
        '''
        s_par = holder.get_params()

        obs : list[zpar] = []
        for par in s_par:
            if par.name not in self.parameters: 
                continue

            if isinstance(par, zpar):
                obs.append(par)

        if not obs:
            for par in s_par:
                log.error(par.name)

            raise ValueError('No observable found')

        ninit = len(self.parameters)
        nzfit = len(obs)

        if ninit != nzfit:
            raise ValueError(f'Number of constraint parameters and zfit parameters differ: {ninit} != {nzfit}')

        return obs
    # ----------------------
    @cached_property
    def observations(self) -> dict[str,zpar]:
        '''
        Returns
        -------------
        List with parameters synbolizing the mean of the ND Gaussian
        '''
        d_obs : dict[str,zpar] = dict()
        for ipar, name in enumerate(self.parameters):
            value = self.values[ipar]
            error = math.sqrt(self.cov[ipar][ipar])

            obs = zfit.Parameter(
                f'{name}_mu', 
                value, 
                value - 5 * error, 
                value + 5 * error)

            d_obs[name] = obs

        return d_obs
    # ---------------------
    def zfit_cons(self, holder : ParsHolder) -> GConstraint:
        '''
        Parameters
        ------------
        holder: Object holding zfit parameters, e.g. Likelihood

        Returns
        ------------
        Multidimentional Gaussian constraint
        '''
        l_par = self._obs_from_holder(holder = holder)
        l_obs = self.observations.values()

        if self.kind == 'GaussianConstraint':
            cns   = zfit.constraint.GaussianConstraint(
                params      = l_par, 
                observation = l_obs,
                cov         = self.cov)
        else:
            raise ValueError(f'Invalid constraint kind: {self.kind}')

        return cns
    # ----------------------
    def observation(self, name : str) -> float:
        '''
        Parameters
        -------------
        name: Name of parameter that will be constrained

        Returns
        -------------
        Value to which it will be constrained
        '''
        if name not in self.observations:
            raise ValueError(f'Parameter {name} not found')

        par = self.observations[name]

        return float(par.value().numpy())
    # ----------------------
    def resample(self) -> None:
        '''
        Sets the value of the constrained parameter to
        '''
        new_values = numpy.random.multivariate_normal(self.values, self.cov, size=1)
        for new_value, observation in zip(new_values[0], self.observations.values(), strict = True):
            observation.set_value(new_value)
# ----------------------------------------
class Constraint1D(Constraint):
    '''
    Class representing Gaussian 1D constrain
    '''
    kind: ConstraintType 
    mu  : float
    sg  : float
    # ----------------------
    @classmethod
    def from_dict(
        cls,
        data : dict[str,tuple[float,float]],
        kind : ConstraintType) -> list['Constraint1D']:
        '''
        Parameters
        -----------------
        data: Dictionary storing parameter names, and tuples with measurements and errors
        kind: String specifying type of constraint

        Returns
        -----------------
        List of 1D constraints
        '''
        constraints : list[Constraint1D] = []
        for name, (value, error) in data.items():
            cns = cls(
                kind = kind,
                name = name,
                mu   = value,
                sg   = error)

            constraints.append(cns)

        return constraints
    # ----------------------
    def calibrate(self, result : FitResult) -> 'Constraint1D':
        '''
        Re-centers mu values of this constraint to value of parameter in holder.
        Needed before fitting toys. The constraints need to be consistent with the
        parameter values used to generate toy data.

        Parameters
        -------------
        result: Object holding result of fit 

        Returns
        -------------
        Copy of this constraint with means calibrated
        '''
        new_value, _ = result[self.name] 

        log.info(f'{self.name:<20}{self.mu:<20.3f}{"--->":<20}{new_value:<20.3f}')

        return Constraint1D(
            kind   = self.kind,
            name   = self.name,
            mu     = new_value, 
            sg     = self.sg,
        )
    # ----------------------
    @cached_property
    def observation(self) -> zpar:
        '''
        Parameter symbolizing mean of Gaussian constraint
        '''
        match self.kind:
            case 'GaussianConstraint':
                sg = self.sg
            case 'PoissonConstraint':
                sg = self.mu
            case _:
                raise ValueError(f'Invalid constraint: {self.kind}')

        mu   = zfit.Parameter(
            f'{self.name}_mu', 
            self.mu, 
            self.mu - 5 * sg,
            self.mu + 5 * sg)

        return mu
    # ----------------------
    def _obs_from_holder(self, holder : ParsHolder) -> zpar:
        '''
        Parameters
        ------------------
        holder: Object holding parameters

        Returns
        ------------------
        Observable of constraint, i.e. parameter to constrain
        '''
        s_par_flt = holder.get_params(floating = True)
        s_par_fix = holder.get_params(floating = False)
        for par in s_par_flt:
            if par.name == self.name and isinstance(par, zpar):
                return par

        log.error('Floating parameters')
        for par in s_par_flt:
            log.error(par.name)

        log.error('Fixed parameters')
        for par in s_par_fix:
            log.error(par.name)

        raise ValueError(f'Cannot find {self.name} in NLL')
    # ----------------------
    def zfit_cons(self, holder : ParsHolder) -> GConstraint | PConstraint:
        '''
        Zfit constraint corresponding to `par`
        '''
        obs = self._obs_from_holder(holder = holder)

        match self.kind:
            case ConstraintType.gauss: 
                cons = GConstraint(
                    params      = obs, 
                    observation = self.observation, 
                    uncertainty = self.sg)
            case ConstraintType.poisson:
                cons = PConstraint(
                    params      = obs, 
                    observation = self.observation)

        return cons
    # ----------------------
    def __str__(self) -> str:
        '''
        Returns
        -------------
        String representation
        '''
        return f'{self.name:<50}{self.mu:<20.3f}{self.sg:<20.3f}{self.kind:<20}'
    # ----------------------
    def resample(self) -> None:
        '''
        Sets the value of the constrained parameter to
        '''
        match self.kind:
            case 'GaussianConstraint':
                new_val = numpy.random.normal(loc=self.mu, scale=self.sg)
            case 'PoissonConstraint':
                new_val = numpy.random.poisson(lam=self.mu)
            case _:
                raise ValueError(f'Invalid constraint kind: {self.kind}')

        self.observation.set_value(new_val)
# ----------------------------------------
class Constraints[C : Constraint](RootModel[Mapping[str,C]]):
    '''
    Class meant to be used as a container of constraint objects

    The key of the mapping is:

    1D: Name of the constrained parameter, e.g. mu
    ND: Name of physical thing constrained, e.g. signal_shape
    '''
# ----------------------------------------
def build_constraint(data: dict) -> Constraint:
    '''
    Parameters
    ---------------
    data: Python dictionary with constraint information

    Returns
    ---------------
    Constraint object
    '''
    adapter = TypeAdapter(Constraint1D | ConstraintND)

    try:
        return adapter.validate_python(data)
    except Exception as exc:
        pprint.pprint(data)
        raise ValueError('Cannot build constrain from input') from exc
# ----------------------------------------
def print_constraints(constraints : Constraints) -> None:
    '''
    Parameters
    -------------
    List of constraint objects
    '''
    l_cons_1d = [ cons for cons in constraints if isinstance(cons, Constraint1D) ]
    l_cons_nd = [ cons for cons in constraints if isinstance(cons, ConstraintND) ]

    if l_cons_1d:
        _print_1d_constraints(l_cons_1d)

    if l_cons_nd:
        _print_nd_constraints(l_cons_nd)
# ----------------------------------------
def _print_1d_constraints(constraints : Sequence[Constraint1D]) -> None:
    '''
    Prints list of constraints
    '''
    log.info(f'{"Parameter":<50}{"Value":<20}{"Error":<20}{"Kind":<20}')
    log.info(80 * '-')
    for constraint in constraints:
        log.info(constraint)
# ----------------------------------------
def _print_nd_constraints(constraints : Sequence[ConstraintND]) -> None:
    '''
    Prints list of constraints
    '''
    for constraint in constraints:
        log.info(constraint)
# ----------------------------------------
