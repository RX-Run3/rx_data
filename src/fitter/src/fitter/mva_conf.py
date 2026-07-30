'''
Module containing MVAConf class
'''
from typing      import Self
from pydantic    import BaseModel, RootModel, model_validator
from contextlib  import contextmanager
from contextvars import ContextVar
from rx_common   import WorkingPoint, Cut, Cuts

_MULT_FACTOR : ContextVar[float] = ContextVar('_MULT_FACTOR', default = 1000.) 
# ---------------------
class MVAWp(RootModel[float|tuple[float,float]]):
    '''
    Class meant to represent an MVA working point

    The value of the config is meant to represent a probability
    i.e. val in [0, 1]
    '''
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
        val: String representing WP, e.g. 0.3 or 0.5-0.8

        Returns
        -------------
        Instance of MVAWp
        '''
        if '-' in val:
            lower, upper = val.split('-')
            values = float(lower), float(upper)

            return cls(values)

        return cls(float(val))
    # -------------    
    @classmethod
    def from_label(cls, val : str) -> Self:
        '''
        Parameters
        -------------
        val: String representing WP, e.g. 030 or 050-080

        Returns
        -------------
        Instance of MVAWp
        '''
        fact = _MULT_FACTOR.get()
        if '-' in val:
            lower, upper = val.split('-')
            values = float(lower) / fact, float(upper) / fact 

            return cls(values)

        return cls(float(val) / fact)
    # -------------    
    @model_validator(mode = 'after')
    def validate_value(self) -> 'MVAWp':
        if isinstance(self.root, (float, int)):
            self._validate_prob(prob = self.root)
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
            return f'{name} > {self.root}'

        min, max = self.root

        return f'({name} < {max}) && ({name} > {min})'
    # -------------    
    @property
    def name(self):
        '''
        Friendlier name for working point, e.g. 523 (0.523)
        '''
        fact = _MULT_FACTOR.get()
        if isinstance(self.root, (float, int)):
            val = int(fact * self.root)
            return str(val)

        low = int(fact * self.root[0])
        hig = int(fact * self.root[1])

        return f'{low:04d}-{hig:04d}'
    # ---------------------------------
    @classmethod
    def mult_factor(cls, value : float):
        '''
        Parameters
        ---------------
        value: Factor needed to switch MVA WP from probability to labels
        '''
        token = _MULT_FACTOR.set(value)
        @contextmanager
        def _context():
            try:
                yield
            finally:
                _MULT_FACTOR.reset(token)

        return _context()
    # -------------    
    def __str__(self):
        if isinstance(self.root, float):
            return f'{self.root:.3f}'

        low, high  = self.root # type: ignore[misc]

        return f'{low:.2f}-{high:.2f}'
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
