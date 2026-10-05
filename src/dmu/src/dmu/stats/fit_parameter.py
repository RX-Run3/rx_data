'''
Module holding FitParameter class
'''
import re

from functools   import cached_property
from gvar        import gvar
from contextlib  import contextmanager
from pydantic    import BaseModel
from dmu         import LogStore
from typing      import Self, Final
from contextvars import ContextVar

_VALIDATE_PAR_NAME : ContextVar[bool] = ContextVar('_validate_par_name', default = False)
_PAR_REGX : Final[str  ] = r'\w+_\w+_\w+_\d+'

log=LogStore.add_logger('fitter:fit_parameter')
# -------------------------------------
class FitParameter(BaseModel, frozen = True):
    '''
    Class meant to represent fitting parameter
    '''
    name : str
    value: float
    error: float
    # ----------------------
    def rename(self, original : str, new : str) -> Self:
        '''
        Returns renamed parameter where:

        {SOMETHING}_{original}...

        --->

        {SOMETHING}_{new}...

        i.e. will replace substring starting with leading '_'
        '''
        if f'_{original }' not in self.name:
            raise ValueError(f'In renaming, {original} not found in {self.name}')

        new_name = self.name.replace(f'_{original}', f'_{new}')

        if self.name == new_name:
            log.error(f'{self.name:<40}{new_name:<40}')
            raise ValueError('Renaming failed')
        else:
            log.debug(f'{self.name:<40}{new_name:<40}')

        return self.model_copy(update = {'name' : new_name})
    # ----------------------
    @property
    def data(self) -> tuple[float,float]:
        '''
        Tuple with value and error of parameter
        '''
        return self.value, self.error
    # ----------------------
    def __mul__(self, other : 'FitParameter') -> 'FitParameter':
        name      = f'{self.name}_prod_{other.name}'
        this_val  = gvar(self.value , self.error )
        other_val = gvar(other.value, other.error)

        res_val   = this_val * other_val

        return FitParameter(name = name, value = res_val.mean, error = res_val.sdev)
    # ----------------------
    def model_post_init(self, _) -> None:
        if not _VALIDATE_PAR_NAME.get():
            return

        mtch = re.match(_PAR_REGX, self.name)

        if not mtch:
            log.error(f'Parameters should follow naming: {_PAR_REGX}')
            raise ValueError(f'Invalid parameter name: {self.name}')
    # ----------------------
    @cached_property
    def prefix(self) -> str:
        '''
        Parameters are meant to be called as

        {PREFIX}_{MODEL}_{COMPONENT}_{INDEX}

        e.g. mu_suj_combinatorial_1

        This will return PREFIX
        '''
        parts = self.name.split('_')
        first = parts[0]

        # If yld_comb_..., yld_sign_...
        # Use yld_comb as prefix
        # Same with scales
        if first in {'yld', 's'}:
            return '_'.join(parts[:2])

        return first
    # ----------------------
    def __str__(self) -> str:
        '''
        Returns
        -------------
        String representation
        '''
        msg = f'{self.name:<50}{self.value:<20.3g}{"±":5}{self.error:<20.3g}'

        return msg
    # ----------------------
    @classmethod
    def enforce_naming_convention(cls, value : bool):
        '''
        Parameters
        --------------
        value: If True (default) will enforce naming convention of fitting parameters
        '''

        @contextmanager
        def _context():
            token = _VALIDATE_PAR_NAME.set(value)

            try:
                yield
            finally:
                _VALIDATE_PAR_NAME.reset(token)

        return _context()

