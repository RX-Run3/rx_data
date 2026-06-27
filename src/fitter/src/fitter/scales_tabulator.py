'''
Module containing ScalesTabulator
'''
import os
 
from pathlib     import Path
from typing      import Final
from pydantic    import BaseModel, model_validator
from dmu.generic import utilities as gut
from rx_common   import Brem, Component, Qsq, Trigger

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------------------------
class ScalesGroup(BaseModel):
    '''
    Class representing a group of signal/background scales
    '''
    trigger    : Trigger
    brem       : Brem
    q2bin      : list[Qsq]
    backgrounds: list[Component]
    signal     : list[Component]
    # ------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data):
        brem = data['brem']
        data['brem'] = Brem.from_str(brem)

        return data
# ----------------------------------------
class ScalesTabulatorConf(BaseModel):
    '''
    Class used to configure ScalesTabulator
    '''
    output_directory : Path
    categories       : dict[str,ScalesGroup]
    # ------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data):
        out_dir = data['output_directory']
        out_dir = _ANADIR / out_dir
        data['output_directory'] = out_dir

        return data
    # ------------------
    @staticmethod
    def load() -> 'ScalesTabulatorConf':
        '''
        Returns
        --------------
        Config object to tabulate scales
        '''
        data = gut.load_data(
            package = 'fitter_data', 
            fpath   = 'scales/config.yaml')

        return ScalesTabulatorConf(**data)
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
