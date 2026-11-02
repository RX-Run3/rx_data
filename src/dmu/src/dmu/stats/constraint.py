'''
Module containing constraint classes 
'''

import yaml
import json
import math
import numpy
import pprint

from scipy.linalg    import block_diag
from typing          import Final, overload
from collections.abc import Mapping
from pathlib         import Path
from typing          import Literal, Self
from tabulate        import tabulate
from functools       import cached_property
from zfit.constraint import GaussianConstraint as GConstraint
from zfit.constraint import PoissonConstraint  as PConstraint
from zfit.param      import Parameter as zpar
from pydantic        import BaseModel, model_validator, TypeAdapter
from pydantic        import RootModel

from dmu             import LogStore
from dmu.generic     import Serializable

from .fit_result     import FitResult
from .protocols      import ParsHolder
from .types          import ConstraintType
from .imports        import zfit

log = LogStore.add_logger('dmu:stats:constraint')

# Size of space where constrained parameter lives, in standard deviations
_CONS_SPACE_SIGMAS : Final[float] = 5

# When merging 1D constraints into ND one, use this ND Constraint
_1D_CONS_TYPE      : Final[ConstraintType] = ConstraintType.gauss
# ----------------------------------------
class Constraint(BaseModel):
    '''
    Class with common code to 1D and ND constraints
    '''
    name : str
    # ----------------------
    def calibrate(self, result : FitResult) -> 'Constraint':
        _ = result
        raise NotImplementedError('calibrate method not implemented')
    # ----------------------
    def resample(self) -> None:
        raise NotImplementedError('resample method not implemented')
    # ----------------------
    def observation(self, name : str, raise_on_missing : bool = True) -> float | None:
        '''
        Parameters
        --------------
        name: Name of constrained parameter

        Returns
        --------------
        Zfit parameter representing observation
        '''
        raise NotImplementedError('observation method not implemented')
    # ----------------------
    def zfit_cons(self, holder : ParsHolder) -> GConstraint | PConstraint:
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
    def __str__(self):
        return 'Base class constraint'
    # ----------------------
    def __lt__(self, other : 'Constraint1D') -> bool:
        '''
        Sort constraints by name
        '''
        return self.name < other.name
# ----------------------------------------
class Constraints[C : Constraint](RootModel[Mapping[str,C]], Serializable, frozen = True):
    '''
    Class meant to be used as a container of constraint objects

    The key of the mapping is:

    1D: Name of the constrained parameter, e.g. mu
    ND: Name of physical thing constrained, e.g. signal_shape
    '''
    # -------------------------------------------
    @classmethod
    def none(cls) -> 'Constraints[Constraint1D | ConstraintND]':
        '''
        Returns instance of constraints holder, holding no constraints
        '''
        return cls(root = dict())
    # -------------------------------------------
    @property
    def one_dim(self) -> 'Constraints[Constraint1D]':
        '''
        Holder of 1D constraints
        '''
        root = { key : val for key, val in self.root.items() if isinstance(key, Constraint1D) }

        return Constraints(root = root)
    # -------------------------------------------
    @property
    def multi_dim(self) -> 'Constraints[ConstraintND]':
        '''
        Holder of ND constraints
        '''
        root = { key : val for key, val in self.root.items() if isinstance(key, ConstraintND) }

        return Constraints(root = root)
    # -------------------------------------------
    def to_list(self) -> list[Constraint]:
        '''
        Returns list of constraints
        '''
        return [ cons for cons in self.root.values() ]
    # -------------------------------------------
    def __str__(self) -> str:
        header_1d = f'{"Parameter":<50}{"Value":<20}{"Error":<20}{"Kind":<20}\n'
        header_1d+= '-' * 110

        l_cons_1d = [ cons for cons in self.root.values() if isinstance(cons, Constraint1D) ]
        l_cons_nd = [ cons for cons in self.root.values() if isinstance(cons, ConstraintND) ]

        msg = ''
        if l_cons_1d:
            msgs  = [ header_1d ] + [ str(cons) for cons in l_cons_1d ]
            msg  += '\n'.join(msgs) + '\n'

        if l_cons_nd:
            msgs  = [ '-' * 110 ] + [ str(cons) for cons in l_cons_nd ]
            msg  += '\n'.join(msgs) + '\n'

        return msg 
    # -------------------------------------------
    def merge(self, name : str) -> 'ConstraintND':
        '''
        Parameters
        ---------
        name: Name of merged constraint

        Returns
        ---------
        Holder of constraints with one ND constraint, resulting from merging
        all constraints
        '''
        l_cons_1d : list[Constraint1D] = [ cons for cons in self.root.values() if isinstance(cons, Constraint1D) ]
        l_cons_nd : list[ConstraintND] = [ cons for cons in self.root.values() if isinstance(cons, ConstraintND) ]

        if l_cons_1d:
            cons_nd_from_1d = self._merge_1d_constraints(
                constraints = l_cons_1d, 
                kind        = _1D_CONS_TYPE)

            l_cons_nd.append(cons_nd_from_1d)

        if len(l_cons_nd) == 1:
            return l_cons_nd[0]

        types = { cons.kind for cons in l_cons_nd }
        if len(types) != 1:
            raise ValueError(f'Found multiple types of 1D constraints: {types}')
        cons_type = types.pop() 

        cons = self._merge_nd_constraints(
            name        = name,
            kind        = cons_type,
            constraints = l_cons_nd)

        return cons 
    # -------------------------------------------
    def _merge_nd_constraints(
        self, 
        name        : str, 
        kind        : ConstraintType,
        constraints : list['ConstraintND']) -> 'ConstraintND':
        '''
        Parameters
        -----------------
        name       : Name of resulting constraint
        constraints: List of ND constraint to merge into an ND one

        Returns
        -----------------
        ND constraint resulting from merging ND ones
        '''
        parameters = [ parameter for cons in constraints for parameter in cons.parameters ]
        values     = [ value     for cons in constraints for value     in cons.values     ]
        covs       = [ cons.cov  for cons in constraints ] 
        cov : list[list[float]] = block_diag(*[ numpy.asarray(c, dtype = float) for c in covs ]).tolist()

        return ConstraintND(
            name       = name,
            kind       = kind,
            parameters = parameters,
            values     = values,
            cov        = cov)
    # -------------------------------------------
    def _merge_1d_constraints(
        self, 
        kind        : ConstraintType,
        constraints : list['Constraint1D']) -> 'ConstraintND':
        '''
        Parameters
        -----------------
        kind       : Type of ND constraint to build, e.g. Gaussian
        constraints: List of 1D constraint to merge into an ND one

        Returns
        -----------------
        ND constraint resulting from merging 1D ones
        '''
        kinds = { cons.kind for cons in constraints }
        if kinds != {_1D_CONS_TYPE}:
            log.error(kinds)
            raise ValueError(f'Not all 1D constraints are of type: {_1D_CONS_TYPE}')

        params = [ cons.name    for cons in constraints ]
        values = [ cons.mu      for cons in constraints ]
        varncs = [ cons.sg ** 2 for cons in constraints ]

        return ConstraintND(
            name       = 'merged_1d',
            kind       = kind,
            parameters = params,
            values     = values,
            cov        = numpy.diag(varncs))
    # -------------------------------------------
    def value(self, name : str) -> float | None:
        '''
        Parameters
        ----------------
        name: Parameter name

        Returns
        ----------------
        Value at which corresponding parameter is constrained, None if not found
        '''
        vals : list[float] = []
        for cons in self.root.values():
            val = cons.observation(name = name, raise_on_missing = False)
            if val is None:
                continue

            vals.append(val)

        if len(vals) == 1:
            return vals[0]

        if len(vals) == 0:
            return None

        raise ValueError(f'Found multiple values for parameter {name}')
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

            log.debug(f'{name:<50}{old_value:<20.3f}{"--->":<20}{new_value:<20.3f}')

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
    def _params_from_holder(self, holder : ParsHolder) -> list[zpar]:
        '''
        Parameters to be constrained as zfit Parameter instances
        '''
        s_flt   = holder.get_params(floating =  True)
        s_fix   = holder.get_params(floating = False)
        s_all   = s_flt | s_fix
        d_holder_params = { par.name : par for par in s_all if par.name in self.parameters }

        try:
            pars = [ d_holder_params[name] for name in self.parameters ] 
        except Exception as exc:
            for name in d_holder_params:
                log.error(name)
            raise ValueError(f'Cannot find at least one parameter associated to a constraint in: {self}') from exc

        return pars
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
        if self.kind != ConstraintType.gauss:
            raise ValueError(f'Invalid constraint kind: {self.kind}')

        params= self._params_from_holder(holder = holder)
        l_obs = self.observations.values()
        cns   = zfit.constraint.GaussianConstraint(
            params      = params, 
            observation = l_obs,
            cov         = self.cov)

        return cns
    # ----------------------
    @overload
    def observation(self, name : str, raise_on_missing : bool =     ...) ->        float:...
    @overload
    def observation(self, name : str, raise_on_missing : Literal[False]) -> None | float:...
    def observation(self, name : str, raise_on_missing : bool = True   ) -> None | float:
        '''
        Parameters
        -------------
        name            : Name of parameter that will be constrained
        raise_on_missing: If True and if parameter is not found, raises ValueError, 
                          If False and not found, returns None

        Returns
        -------------
        Value to which it will be constrained, None if name is wrong
        '''
        par = self.observations.get(name)
        if par is not None:
            return float(par.value().numpy())

        if not raise_on_missing:
            return None

        raise ValueError(f'Missing value: {name}')
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
    name: str
    kind: ConstraintType 
    mu  : float
    sg  : float
    # ----------------------
    @classmethod
    def from_dict(
        cls,
        data : dict[str,tuple[float,float]],
        kind : ConstraintType) -> Constraints['Constraint1D']:
        '''
        Parameters
        -----------------
        data: Dictionary storing parameter names, and tuples with measurements and errors
        kind: String specifying type of constraint

        Returns
        -----------------
        List of 1D constraints
        '''
        constraints : dict[str,Constraint1D] = dict()
        for name, (value, error) in data.items():
            cns = cls(
                kind = kind,
                name = name,
                mu   = value,
                sg   = error)

            constraints[name] = cns

        return Constraints[Constraint1D](root = constraints) 
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
    def obs(self) -> zpar:
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
            name  = f'{self.name}_mu', 
            value = self.mu, 
            lower = self.mu - _CONS_SPACE_SIGMAS * sg,
            upper = self.mu + _CONS_SPACE_SIGMAS * sg)

        return mu
    # ----------------------
    @overload
    def observation(self, name : str, raise_on_missing : bool =     ...) ->        float:...
    @overload
    def observation(self, name : str, raise_on_missing : Literal[False]) -> None | float:...
    def observation(self, name : str, raise_on_missing : bool = True   ) -> None | float:
        '''
        Parameters
        -------------
        name            : Name of parameter that will be constrained
        raise_on_missing: If True and if parameter is not found, raises ValueError, 
                          If False and not found, returns None

        Returns
        -------------
        None if parameter does not match name attribute, observation value otherwise
        '''
        if name == self.name:
            return self.mu

        if raise_on_missing:
            raise ValueError(f'Missing parameter: {name}')

        return None
    # ----------------------
    @property
    def current_observation(self) -> float:
        '''
        Value of `mu` at this moment. Can differ from `self.mu`
        if constraint is been resampled for e.g. toys
        '''
        return self.obs.numpy()
    # ----------------------
    def _param_from_holder(self, holder : ParsHolder) -> zpar:
        '''
        Parameters
        ----------------
        holder: Object storing parameters to constrain (e.g. likelihood)

        Returns
        ----------------
        Parameter been constrained, taken from holder (e.g. likelihood)
        '''
        s_flt   = holder.get_params(floating =  True)
        s_fix   = holder.get_params(floating = False)
        s_all   = s_flt | s_fix
        l_par   = [ par for par in s_all if par.name == self.name ]

        if len(l_par) != 1:
            for par in l_par:
                log.error(par.name)
            raise ValueError(f'Not found one and only one parameter named: {self.name}')

        return l_par[0]
    # ----------------------
    def zfit_cons(self, holder : ParsHolder) -> GConstraint | PConstraint:
        '''
        Zfit constraint corresponding to `par`
        '''
        param = self._param_from_holder(holder = holder)

        match self.kind:
            case ConstraintType.gauss: 
                cons = GConstraint(
                    params      = param, 
                    observation = self.obs, 
                    uncertainty = self.sg)
            case ConstraintType.poisson:
                cons = PConstraint(
                    params      = param, 
                    observation = self.obs)

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

        self.obs.set_value(new_val)
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
