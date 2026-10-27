'''
Module containing MVAConf class
'''
from typing         import Self, Final
from pydantic       import BaseModel, RootModel, model_validator
from .working_point import WorkingPoint
from .cuts          import Cut, Cuts

_UNINIT_NAME : Final[str]     = 'default'
'''Label associated to value of MVAWp when no custom value was used'''

UNINIT_VAL  : Final[float]    = -999.
'''Value used as placeholder for MVAWp that are meant to
represent the absence of a working point, e.g. such that 
default analysis values are used'''

_MULT_FACTOR : Final[float]    = 1000.
'''Needed to go back and forth from string representation'''

_LEN_STR     : Final[set[int]] = {3, 4}
'''String representation of MVAWp should be like 0100 (new) or 100 (old)'''
# ---------------------
class MVAWp(RootModel[float|tuple[float,float]]):
    '''
    Class meant to represent an MVA working point

    The value of the config is meant to represent a probability
    i.e. val in [0, 1]
    '''
    # ----------------------
    @classmethod
    def none(cls) -> 'MVAWp':
        '''
        Instance of WP meant to represent no cut
        '''
        val = UNINIT_VAL, UNINIT_VAL

        return cls(root = val)
    # ----------------------
    @classmethod
    def from_wp(cls, wp : WorkingPoint, is_cmb : bool) -> 'MVAWp':
        '''
        Parameters
        ----------------
        wp    : Generic working point
        is_cmb: If true will extract combinatorial WP, otherwise part reco
        '''
        target : Cut | None = None
        for cut in wp.root:
            if cut.cut == Cuts.cmb and     is_cmb:
                if target is not None:
                    raise ValueError(f'Cut found multiple times in: {wp}')

                target = cut

            if cut.cut == Cuts.prc and not is_cmb:
                if target is not None:
                    raise ValueError(f'Cut found multiple times in: {wp}')

                target = cut

        if target is None:
            raise ValueError(f'Could not find cut in: {wp}')

        return cls(root = target.val)
    # -------------    
    @property
    def lower_str(self) -> str:
        return f'{self.lower:.03f}'
    # -------------    
    @property
    def upper_str(self) -> str:
        return f'{self.upper:.03f}'
    # -------------    
    @property
    def lower(self) -> float:
        '''
        Lower bound of working point
        '''
        if isinstance(self.root, float):
            return self.root

        if isinstance(self.root, tuple):
            return self.root[0]

        raise ValueError(f'Invalid WP: {self.root}')
    # -------------    
    @property
    def upper(self) -> float:
        '''
        Upperbound of working point
        '''
        if isinstance(self.root, float):
            return 1.0 

        if isinstance(self.root, tuple):
            return self.root[1]

        raise ValueError(f'Invalid WP: {self.root}')
    # -------------    
    @classmethod
    def from_str(cls, val : str) -> Self:
        '''
        Parameters
        -------------
        val: String representing WP, e.g. 0300 or 0500-0800

        Returns
        -------------
        Instance of MVAWp
        '''
        if '-' in val:
            lower, upper = val.split('-')
            lo     = cls.__str_to_float(val = lower) 
            hi     = cls.__str_to_float(val = upper) 
            values = lo, hi

            return cls(values)

        flt_val = cls.__str_to_float(val = val)

        return cls(flt_val)
    # -------------    
    @classmethod
    def __str_to_float(cls, val : str) -> float:
        '''
        Takes string representing float, returns float 
        '''
        if not val.isnumeric():
            raise ValueError(f'{val} is not numeric')

        if len(val) not in _LEN_STR:
            raise ValueError(f'{val} expected to have {_LEN_STR} decimals')

        return float(val) / _MULT_FACTOR
    # -------------    
    @model_validator(mode = 'before')
    @classmethod
    def validate_input(cls, data):
        if isinstance(data, str):
            wp = MVAWp.from_str(data)
            return wp.root

        return data
    # -------------    
    @model_validator(mode = 'after')
    def validate_value(self) -> 'MVAWp':
        if isinstance(self.root, (float, int)):
            self._validate_prob(prob = self.root)
            return self

        if self.lower == UNINIT_VAL and self.upper == UNINIT_VAL:
            return self

        low, high = self.root

        if low >= high:
            raise ValueError(f'Invalid working point: {self}')

        self._validate_prob(prob =  low)
        self._validate_prob(prob = high)

        return self
    # -------------    
    def _validate_prob(self, prob : float):
        if 0 <= prob <= 1:
            return
        
        raise ValueError(f'Invalid probability: {prob}')
    # ----------------------
    def get_cut(self, name : str) -> str:
        '''
        Parameters
        --------------
        name: Name of branch on which the cut is applied, e.g. mva_cmb
        '''
        if isinstance(self.root, (float, int)):
            return f'{name} >= {self.root}'

        min_val, max_val = self.root

        return f'({name} >= {min_val}) && ({name} < {max_val})'
    # -------------    
    @property
    def name(self):
        '''
        Friendlier name for working point, e.g. 0523 for 0.523
        '''
        if self == MVAWp.none():
            return _UNINIT_NAME

        if isinstance(self.root, (float, int)):
            val = int(_MULT_FACTOR * self.root)
            return f'{val:04d}'

        low = int(_MULT_FACTOR * self.root[0])
        hig = int(_MULT_FACTOR * self.root[1])

        return f'{low:04d}-{hig:04d}'
    # -------------    
    def __str__(self):
        if isinstance(self.root, float):
            return f'{self.root:.3f}'

        low, high  = self.root # type: ignore[misc]

        return f'{low:.2f}-{high:.2f}'
    # -------------    
    def __format__(self, spec : str):
        return format(str(self), spec)
# ---------------------
class MVAConf(BaseModel):
    '''
    Class meant to hold configuration for MVA
    working point
    '''
    cmb : MVAWp
    prc : MVAWp
    # ----------------------
    @classmethod
    def from_values(
        cls,
        cmb : float | tuple[float,float],
        prc : float | tuple[float,float]) -> 'MVAConf':
        '''
        Builds MVAConf from numerical values of working point
        '''
        mva_cmb = MVAWp(root = cmb)
        mva_prc = MVAWp(root = prc)

        return cls(cmb = mva_cmb, prc = mva_prc)
    # ----------------------
    def __str__(self):
        value = f'CMB: {self.cmb}\n'
        value+= f'PRC: {self.prc}'

        return value
# ---------------------
