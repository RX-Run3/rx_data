'''
This module contains the ConstraintAdder class
'''
import numpy

from contextlib      import contextmanager
from dmu             import LogStore
from typing          import cast
from omegaconf       import DictConfig
from zfit            import Parameter
from zfit.loss       import ExtendedUnbinnedNLL
from .constraint     import Constraints
from .imports        import zfit

log = LogStore.add_logger('dmu:stats:constraint_adder')
# ----------------------
class ConstraintAdder:
    '''
    This class is in charge of:

    - Using those constraints to update the NLL
    '''
    _fix_parameters = False
    # ----------------------
    def __init__(
        self, 
        nll         : ExtendedUnbinnedNLL, 
        constraints : Constraints):
        '''
        Parameters
        -------------
        nll        : Zfit likelihood, before constraints added
        constraints: List of constraint objects
        '''
        self._nll         = nll
        self._constraints = constraints

        self._d_par = self._get_params(nll=nll)
        self._d_cns : dict[str,Parameter] = {}
    # ----------------------
    def _get_params(self, nll : ExtendedUnbinnedNLL) -> dict[str, Parameter]:
        '''
        Parameters
        -------------
        nll: Likelihood holding parameters

        Returns
        -------------
        Dictionary mapping parameter names with parameters
        '''
        s_par = nll.get_params(floating=True)
        if len(s_par) == 0:
            raise ValueError('No floating parameter found in likelihood')

        return { par.name : cast(Parameter, par) for par in s_par }
    # ----------------------
    def _get_observation(self, cfg : DictConfig) -> list[Parameter]:
        '''
        Parameters
        -------------
        cfg  : Configuration specifying how to build the Gaussian constraint
        mode : Controls the observation value. Either toy or real.

        Returns
        -------------
        List of observations as parameters
        '''
        l_nam = cfg.parameters
        l_val = cfg.observation
        l_par = [ zfit.Parameter(f'{nam}_cns', fval) for nam, fval in zip(l_nam, l_val, strict = True) ]

        return l_par
    # ----------------------
    def _update_observations(self, values : numpy.ndarray, names : list[str]) -> None:
        '''
        This method sets the values of the constraining parameters from resampled values

        Parameters
        -------------
        values: Array with resampled observations
        names : Names of parameters used to constrain likelihood
        '''
        for name, value in zip(names, values, strict = True):
            log.verbose(f'Setting {name}={value}')

            if name not in self._d_cns:
                raise ValueError(f'Cannot find constraining parameter: {name}')

            par = self._d_cns[name]
            par.set_value(value)
    # ----------------------
    def __fix_parameters(self) -> None:
        '''
        Fixes NLL parameters based on central values of constraints
        '''
        log.warning('Fixing parameters instead of constraining them')
        pars : set[Parameter] = self._nll.get_params()
        for par in pars:
            value = self._constraints.value(name = par.name)
            if value is None:
                continue

            log.debug(f'{par.name:<30}{value:<20.3g}')
            par.set_value(value)
            par.floating = False
    # ----------------------
    @classmethod
    @contextmanager
    def fixed_parameters(cls):
        '''
        Contextmanager whose context makes ConstraintAdder fix parameters
        instead of constrain them
        '''
        old_value = cls._fix_parameters

        try:
            cls._fix_parameters = True
            yield
        finally:
            cls._fix_parameters = old_value
    # ----------------------
    def get_nll(self) -> ExtendedUnbinnedNLL:
        '''
        Returns
        -------------
        Likelihood with constrain added
        '''
        if self._constraints is None:
            log.info('No constraints found, using original (unconstrained) NLL')
            return self._nll

        if self._fix_parameters:
            self.__fix_parameters()
            return self._nll

        l_const = [ 
            cns.zfit_cons(holder = self._nll)
            for cns in self._constraints.root.values() ]

        nll = self._nll.create_new(constraints=l_const)
        if nll is None:
            raise ValueError('Could not create a new likelihood')

        return nll
# ----------------------
