'''
Module holding classes associated to fit yields
'''
import math

from dmu.generic     import utilities as gut
from pydantic        import RootModel, BaseModel, model_validator
from rx_common       import Component, Project, Trigger
from rx_efficiencies import Efficiency, WorkingPoint
from dmu             import LogStore

log=LogStore.add_logger('rx_efficiencies:yields')
# ----------------------------------------
class ProjectConf(BaseModel):
    '''
    Class holding configuration
    '''
    trigger       : Trigger
    signal        : Component
    normalization : Component
# ----------------------------------------
class YieldCalculatorConf(BaseModel):
    '''
    Class used to hold configuration
    '''
    fits : str
    rk   : ProjectConf
    rkst : ProjectConf
    # --------------------
    @classmethod
    def from_name(cls, name : str) -> 'YieldCalculatorConf':
        '''
        Parameters
        -----------------
        name: string identifying file holding configuration, e.g. rare 

        Returns
        -----------------
        Configuration object
        '''
        data = gut.load_data(
            package = 'fitter_data', 
            fpath   = f'yields/{name}.yaml')

        return cls(**data)
# ----------------------------------------
class Yield(BaseModel):
    '''
    Class used to represent yields
    '''
    val : float
    err : float
    wp  : WorkingPoint
    # ----------------------------------------
    def __str__(self) -> str:
        msg = f'''
        Value: {self.val:.3g}
        Error: {self.err:.3g}
        '''

        return msg
    # ----------------------------------------
    def __check_wpt(self, eff : Efficiency) -> None:
        '''
        Checks that working points for yield and efficiency are the same

        Parameters
        ---------------
        eff: Efficiency object
        '''
        if eff.wp == self.wp:
            return

        log.error(f'Efficiency: {eff.wp} ')
        log.error(f'Yield     : {self.wp}')

        raise ValueError('Working points differ')
    # ----------------------------------------
    def __mul__(self, other : Efficiency) -> 'Yield':
        '''
        Parameters
        --------------
        other: Object representing efficiency

        Returns
        --------------
        Object representing product of efficiency and yield
        errors are propagated without correlation
        '''
        self.__check_wpt(eff = other)

        val = self.val * other.val
        var = (self.val * other.err) ** 2 + (self.err * other.val) ** 2
        err = math.sqrt(var)

        return Yield(val = val, err = err, wp = self.wp)
    # ----------------------------------------
    def __rmul__(self, other : Efficiency) -> 'Yield':
        return self.__mul__(other)
    # ----------------------------------------
    def __truediv__(self, other : Efficiency) -> 'Yield':
        '''
        Parameters
        --------------
        other: Object representing efficiency

        Returns
        --------------
        Object representing ratio yield and efficiency
        errors are propagated without correlation
        '''
        self.__check_wpt(eff = other)

        val = self.val / other.val
        rat = (self.err / self.val) ** 2 + (other.err / other.val) ** 2
        err = val * math.sqrt(rat)

        return Yield(val = val, err = err, wp = self.wp)
    # ----------------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Yield':
        if self.err <= 0.:
            raise ValueError(f'Yield error cannot be zero or negative, found: {self.err}')

        return self
# ----------------------------------------
class YieldGrid(RootModel[list[Yield]]):
    '''
    Class meant to represent a collection of yields
    '''
# ----------------------------------------
class YieldCalculator:
    '''
    Class used to calculate expected yields based
    on resonant mode yields and efficiencies
    '''
    # -------------------------------
    def __init__(self, name : str, project : Project):
        '''
        Parameters
        ---------------
        cfg: Object holding configuration
        '''
        self.__cfg = YieldCalculatorConf.from_name(name = name) 
        self.__prj = project
    # -------------------------------
    def calculate(self) -> YieldGrid:
        '''
        Returns
        --------------
        Yield grid, e.g. holder of yields
        '''
# ----------------------------------------
