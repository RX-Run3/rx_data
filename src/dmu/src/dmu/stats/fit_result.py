'''
Module containing FitResult class
'''
import copy
import math
import yaml
import json
import numpy
import pandas as pnd

from typing           import Self, Sequence
from pathlib          import Path
from pydantic         import BaseModel, Field
from dmu              import LogStore

from .exceptions      import ErrorFailError
from .imports         import zfit
from .goodness_of_fit import GoodnessOfFit
from .fit_parameter   import FitParameter

log = LogStore.add_logger('rx_stats:fit_result')

type zres = zfit.result.FitResult
type zpar = zfit.param.Parameter
# -------------------------------------
class FitResult(BaseModel, frozen = True):
    '''
    Class meant to represent fit result
    '''
    valid      : bool
    status     : int
    gof        : GoodnessOfFit | None = None
    extra_pars : list[FitParameter]   = Field(default_factory = list, description = 'E.g. parameters derived from main parameters')
    parameters : tuple[FitParameter,...]
    covariance : list[list[float]]
    # ----------------------
    def extend(self, pars : list[FitParameter]) -> 'FitResult':
        '''
        Parameters
        -----------------
        pars: Tuple of FitParameter objects used to attach to current object

        Returns
        -----------------
        Copy of current object with extra parameters
        '''
        fail = False
        for par in pars:
            if par.name in self:
                fail = True
                log.error(par)

        if fail:
            raise ValueError('Cannot extend FitResult with parameters already found')

        extra_pars = copy.deepcopy(self.extra_pars)
        extra_pars.extend(pars)
        data = {'extra_pars' : extra_pars}

        return self.model_copy( update = data )
    # ----------------------
    @property
    def __all_parameters(self) -> Sequence[FitParameter]:
        return list(self.parameters) + self.extra_pars
    # ----------------------
    @property
    def df(self) -> pnd.DataFrame:
        '''
        Dataframe with parameter names values and errors
        as columns
        '''
        l_data : list[dict] = []
        for parameter in self.__all_parameters:
            data = {
                'Parameter' : parameter.name,
                'Value'     : parameter.value,
                'Error'     : parameter.error,
            }

            l_data.append(data)

        return pnd.DataFrame(l_data)
    # ----------------------
    @property
    def cov_status(self) -> int:
        '''
        0 if covariance matrix is OK
        '''
        if numpy.isnan(self.covariance).any():
            return 1

        return 0
    # ----------------------
    @classmethod
    def merge(cls, results : list[Self]) -> Self:
        '''
        Parameters
        --------------
        results: List of fit results

        Returns
        --------------
        Fit result object, resulting from adding up all the parameters
        only parameters are kept, everything else is set to a default
        '''
        pars : tuple[FitParameter,...] = tuple(par for result in results for par in result.parameters)

        return cls(
            valid      = True,
            status     = 0,
            covariance = [],
            parameters = pars,
            gof        = None)
    # ----------------------
    def __hash__(self) -> int:
        cov  = tuple( tuple(row) for row in self.covariance )
        pars = tuple(self.__all_parameters)
        data = cov, self.valid, self.status, pars, self.gof

        return hash(data)
    # ----------------------
    def _get_parameter_indexes(self, pars : list[str]) -> list[int]:
        '''
        Parameters
        -------------
        pars: List of prefixes of names of parmeters

        Returns
        -------------
        List of indices of corresponding parameters
        '''
        prefixes : set[str] = { par.prefix for par in self.parameters }
        if len(prefixes) != len(self.parameters):
            for par in self.parameters:
                log.error(par.name)

            raise ValueError('Repeated prefixes found, cannot retrieve parameter indexes safely')

        indexes : list[int] = []
        for index, par in enumerate(self.parameters):
            if par.prefix not in pars:
                continue

            indexes.append(index)

        return indexes
    # ----------------------
    def pars_covariance(self, pars : list[str]) -> list[list[float]]:
        '''
        Parameters
        -------------
        pars: List of prefixes of names of parameters

        Returns
        -------------
        Covariance matrix among parameters
        '''
        indexes : list[int] = self._get_parameter_indexes(pars = pars)

        reduced_cov : list[list[float]] = []
        for irow, row in enumerate(self.covariance):
            if irow not in indexes:
                continue

            this_row : list[float] = []
            for icol, val in enumerate(row):
                if icol not in indexes:
                    continue

                this_row.append(val)

            reduced_cov.append(this_row)

        return reduced_cov
    # ----------------------
    def __lt__(self, other : 'FitResult') -> bool:
        '''
        Better fit is greater
        '''
        if self.gof is None:
            raise ValueError('No GOF defined for this instance')

        if other.gof is None:
            raise ValueError('No GOF defined for other instance')

        return self.gof < other.gof
    # ----------------------
    def __getitem__(self, name : str) -> tuple[float,float]:
        '''
        Parameters
        -------------
        name: Name of parameter

        Returns
        -------------
        Tuple with fit value and error
        '''
        for par in self.__all_parameters:
            if par.name != name:
                continue

            return par.value, par.error

        raise ValueError(f'Parameter {name} not found in:\n {self}')
    # ----------------------
    def __contains__(self, name : str) -> bool:
        '''
        Parameters
        -------------
        name: Parameter name

        Returns
        -------------
        True if parameter exists in fit result
        '''
        return any(par.name == name for par in self.__all_parameters)
    # ----------------------
    def get(self, name : str, fall_back : float | None) -> tuple[float,float]:
        '''
        Parameters
        ----------------
        name     : Name of parameter
        fall_back: Replacement for value and error if parameter not found
                   If None, will raise if parameter is not found

        Returns
        ----------------
        Tuple with value and error
        '''
        for par in self.__all_parameters:
            if par.name != name:
                continue

            return par.value, par.error

        if fall_back is None:
            log.error(self)
            raise ValueError(f'Parameter {name} not found')

        return fall_back, fall_back
    # ----------------------
    def __str__(self) -> str:
        '''
        Returns
        -------------
        String representation
        '''

        msg  = '\n'
        msg += 100 * '-' + '\n'
        msg += f'{"Name":<50}{"Value":<20}{"":<5}{"Error":<20}\n'
        msg += 100 * '-' + '\n'
        for par in self.__all_parameters:
            msg += str(par) + '\n'

        return msg
    # ----------------------
    def to_json(
        self,
        path : Path) -> None:
        '''
        Parameters
        --------------
        path: Path to JSON file
        '''
        data = self.model_dump_json(indent = 2)

        log.info(f'Saving to: {path}')

        path.write_text(data = data)
    # ----------------------
    def set_pars(self, pars : set[zpar]) -> set[zpar]:
        '''
        Parameters
        -------------
        pars: Set of parameters

        Returns
        -------------
        Set of parameters with values set as in current object
        '''
        fail = False
        for par in pars:
            value, _ = self.get(par.name, fall_back=math.nan)
            if math.isnan(value):
                fail = True
                log.error(par.name)
            else:
                par.set_value(value)

        if fail:
            raise ValueError('At least one parameter not found in result')

        return pars
    # ----------------------
    def fix_pars(self, pars : set[zpar]) -> set[zpar]:
        '''
        Parameters
        -------------
        pars: Set of parameters

        Returns
        -------------
        Set of parameters with values fixed as in current object
        '''
        pars = self.set_pars(pars = pars)

        for par in pars:
            par.floating = False

        return pars
    # ----------------------
    def get_pars(self, prefix : str) -> list[FitParameter]:
        '''
        Parameters
        --------------
        prefix: Starting substring in parameter name, e.g. {prefix}mu_gauss

        Returns
        --------------
        Set of parameters starting with prefix
        '''
        all_pars = list(self.parameters) + self.extra_pars

        return [ par for par in all_pars if par.name.startswith(prefix) ]
    # ----------------------
    def get_par(self, prefix : str) -> FitParameter:
        '''
        Parameters
        -----------------
        prefix: Starting substring of parameter name

        Returns
        -----------------
        Parameter whose name matches prefix, if not found one and only one
        will raise exception
        '''
        pars = self.get_pars(prefix = prefix)
        if len(pars) != 1:
            log.error(self)
            raise ValueError(f'Not found one and only one parameter matching prefix: {prefix}')

        return pars[0]
    # ----------------------
    def rename(self, original : str, new : str) -> Self:
        '''
        Parameters
        ----------------
        original: Original name of parameters
        new     : New name of parametes
        '''
        new_pars = [ old_par.rename(original, new) for old_par in self.parameters ]
        ext_pars = [ ext_par.rename(original, new) for ext_par in self.extra_pars ]

        data = {
            'extra_pars' : ext_pars,
            'parameters' : new_pars}

        return self.model_copy(update = data)
    # ----------------------
    @classmethod
    def _par_from_zfit(
        cls,
        name        : str,
        no_errors_ok: bool,
        data        : dict) -> 'FitParameter':
        '''
        Parameters
        -------------
        name        : Parameter name
        data        : Dictionary holding data from parameter fit
        no_errors_ok: If true, it will return nan when errors are missing

        Returns
        -------------
        FitParameter
        '''
        if 'minuit_hesse' in data:
            error : float = data['minuit_hesse']['error']
        elif no_errors_ok:
            error : float = math.nan
        else:
            log.error(data)
            raise ErrorFailError(f'Cannot extract error from parameter: {name}')

        try:
            value : float = data['value']
        except KeyError as exc:
            log.error(data)
            raise KeyError(f'Cannot extract value from parameter: {name}') from exc

        return FitParameter(
            name = name,
            value= float(value),
            error= float(error))
    # ----------------------
    @classmethod
    def from_zfit(
        cls,
        res          : zres,
        gof          : GoodnessOfFit | None = None,
        no_errors_ok : bool                 = False) -> 'FitResult':
        '''
        Parameters
        ---------------
        res         : Zfit fitting result
        gof         : Optional goodness of fit object
        no_errors_ok: If true, it won't raise exception if error not found

        Returns
        ---------------
        Fitting result
        '''
        l_par : list[FitParameter] = []
        for par, data in res.params.items():
            param = cls._par_from_zfit(
                no_errors_ok = no_errors_ok,
                name         = par.name,
                data         = data) # type: ignore

            l_par.append(param)

        pars = tuple(l_par)

        if hasattr(res, 'cov'):
            covariance : numpy.ndarray = res.cov # type: ignore
        else:
            covariance : numpy.ndarray = res.covariance()

        if numpy.isnan(covariance).any():
            log.warning('Found at least one NaN in covariance')

        return cls(
            covariance = covariance.tolist(),
            status     = res.status,
            valid      = res.valid,
            gof        = gof,
            parameters = pars)
    # ----------------------
    @classmethod
    def from_json(
        cls,
        path : Path) -> 'FitResult':
        '''
        Parameters
        --------------
        path: Path to JSON file
        '''
        if not path.exists():
            raise FileNotFoundError(f'File not found: {path}')

        data = path.read_text()

        return cls.model_validate_json(json_data = data)
    # ----------------------
    @classmethod
    def from_yaml(
        cls,
        path : Path) -> 'FitResult':
        '''
        Parameters
        --------------
        path: Path to YAML file
        '''
        if not path.exists():
            raise FileNotFoundError(f'File not found: {path}')

        with open(path) as ifile:
            data = yaml.safe_load(ifile)

        json_string = json.dumps(data)

        return cls.model_validate_json(json_data = json_string)
# -------------------------------------
