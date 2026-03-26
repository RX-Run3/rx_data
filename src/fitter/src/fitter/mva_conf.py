'''
Module containing MVAConf class
'''
from pydantic  import BaseModel, RootModel, model_validator

# ---------------------
class MVAWp(RootModel[float|tuple[float,float]]):
    '''
    Class meant to represent an MVA working point

    The value of the config is meant to represent a probability
    i.e. val in [0, 1]
    '''
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

        return f'({self.root} < {max}) && ({self.root} > {min})'
    # -------------    
    @property
    def name(self):
        '''
        Frientlier name for working point
        Needed to name directories, etc
        '''
        if isinstance(self.root, (float, int)):
            val = int(1000 * self.root)
            return str(val)

        low = int(1000 * self.root[0])
        hig = int(1000 * self.root[1])

        return f'{low}-{hig}'
    # -------------    
    def __str__(self):
        if isinstance(self.root, float):
            return f'{self.root:.3f}'

        low, high  = self.root # type: ignore[misc]

        return f'{low:.3f}-{high:.3f}'
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
    @staticmethod
    def str_to_wp(value : str) -> float:
        '''
        Parameters
        -------------
        value: String representation of Working point, e.g. 300

        Returns
        -------------
        Tuple with low bound and optionally high bound
        '''
        ivalue = int(value)
        if not (0 <= ivalue < 1000):
            raise ValueError(f'Invalid working point: {value}')

        return ivalue / 1000.
    # -------------    
    def __str__(self):
        value = f'CMB: {self.cmb}\n'
        value+= f'PRC: {self.prc}'

        return value
# ---------------------
