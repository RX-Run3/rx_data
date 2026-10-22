'''
Module holding SignalConstraints class
'''
import re

from typing        import Final
from dmu           import LogStore
from dmu.stats     import Constraint, Constraint1D, ConstraintType, ParsHolder
from rx_common     import Block, Brem, Channel, Correction, Component
from zfit.param    import Parameter as zpar
from rx_q2         import ScaleReader

log=LogStore.add_logger('fitter:signal_constraints')

_RGXPR : Final[str] = r'brem_(xx\d)_b(\d)_(?:rk|rkst)_(?:ee|mm)_(scale|reso)_flt'
'''Regex for non-fractions'''
_RGXFR : Final[str] = r'(brem|block)_brem_([x012]{3})_b(\d)(_reso)?_flt'
'''Regex for fractions'''
# ------------------------------------------
class SignalConstraints:
    '''
    Class used to provide constraints for signal, given the likelihood, it will:

    - Find the parameters to constrain (scale, resolution, etc)
    - Search for the constrain values in a database
    - Build the constrain objects and return them in a list

    Conventions:

    - The signal parameters will be named with `COMPONENT_brem_xxX_bY`
      as part of the model name, to indicate the signal type, brem category and the block.
    '''
    # ----------------------
    def __init__(
        self, 
        channel : Channel,
        nll     : ParsHolder,
        comp    : Component):
        '''
        Parameters
        -------------
        nll    : Likelihood or any object with get_params implemented
        comp   : Component that needs to be constrained
        channel: Either ee or mm, needed to pick correct mass scales and resolutions
        '''
        self._nll   = nll
        self._comp  = comp
        self._srd   = ScaleReader(channel = channel)

        self._constraint_kind : ConstraintType = ConstraintType.gauss
    # ----------------------
    def _get_constraint(
        self, 
        brem  : Brem, 
        block : Block, 
        kind  : Correction, 
        par   : zpar) -> Constraint:
        '''
        Parameters
        -------------
        brem : E.g. 1
        block: E.g. 2
        kind : E.g. reso, scale
        par  : Parameter to constrain

        Returns
        -------------
        Constraint object
        '''
        val, err = self._srd.get_scale(
            corr  = kind, 
            block = block, 
            brem  = brem)

        log.debug(f'Constraining: {par.name}')
        log.debug(f'{"Value":<20}{val:20.3f}')
        log.debug(f'{"Error":<20}{err:20.3f}')

        return Constraint1D(
            name = par.name,
            kind = self._constraint_kind,
            mu   = val,
            sg   = err)
    # ----------------------
    def _get_correction_settings(self, par : zpar) -> tuple[Brem, Block, Correction] | None:
        '''
        Parameters
        -------------
        par: Zfit parameter

        Returns
        -------------
        Tuple with settings to find correction
        or None, if no correction (through constraint) is possible for parameter
        '''
        name   = par.name
        _REGEX = f'fr_{self._comp}_{_RGXFR}' if name.startswith('fr') else f'.*{self._comp}_{_RGXPR}'

        mtch = re.match(_REGEX, name)
        if not mtch:
            log.debug(f'Cannot extract, brem, block and kind from: {name}')
            log.debug(f'Using regex: {_REGEX}')
            return

        if name.startswith('fr_'):
            brem = Brem.from_str(value = mtch.group(2)) 
            block= Block(value = int(mtch.group(3)))
            kind = mtch.group(1) 
        else:
            brem = Brem.from_str(value = mtch.group(1)) 
            block= Block(value = int(mtch.group(2)))
            kind = mtch.group(3)

        if   kind == 'scale':
            corr = Correction.mass_scale
        elif kind == 'reso':
            corr = Correction.mass_resolution
        elif kind == 'brem':
            corr = Correction.brem_fraction
        elif kind == 'block':
            corr = Correction.blok_fraction
        else:
            raise ValueError(f'Cannot determine correction for parameter: {name}')

        return brem, block, corr
    # ----------------------
    def get_constraints(self) -> list[Constraint]:
        '''
        Returns
        -------------
        List of constraints
        '''
        constraints : list[Constraint] = []

        s_all_par = self._nll.get_params(floating = True, is_yield = False)
        for par in s_all_par:
            if not isinstance(par, zpar):
                raise ValueError(f'Found non-parameter object: {par}')

            correction_settings = self._get_correction_settings(par = par)
            if correction_settings is None:
                log.debug(f'Not found constraints for {par.name}')
                continue

            brem, block, kind = correction_settings

            constraint = self._get_constraint(
                brem = brem, 
                block= block,
                kind = kind,
                par  = par)

            constraints.append(constraint)

        return constraints
# ------------------------------------------
