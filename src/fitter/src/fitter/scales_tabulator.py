'''
Module containing ScalesTabulator
'''
from pydantic import BaseModel

# ----------------------------------------
class ScalesTabulatorConf(BaseModel):
    '''
    Class used to configure ScalesTabulator
    '''
    # ------------------
    @staticmethod
    def load() -> 'ScalesTabulatorConf':
        return ScalesTabulatorConf()
# ----------------------------------------
class ScalesTabulator:
    '''
    Class used to tabulate signal/background scale factors
    '''
    # ----------------------------------------
    def __init__(self, cfg : ScalesTabulatorConf):
        '''
        Parameters
        ---------------
        cfg: Configuration object
        '''
        self._cfg = cfg
    # ----------------------------------------
    def run(self) -> None:
        '''
        Runs plotting
        '''
# ----------------------------------------
