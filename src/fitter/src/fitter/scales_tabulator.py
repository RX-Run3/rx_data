'''
Module containing ScalesTabulator
'''
import os
import pandas as pnd
 
from dmu.workflow import Cache
from pathlib      import Path
from typing       import Final
from dmu          import LogStore
from pydantic     import BaseModel, model_validator
from dmu.generic  import utilities as gut
from rx_common    import Brem, Component, Qsq, Trigger
from fitter       import PrecScales

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
log = LogStore.add_logger('fitter:scales_tabulator')
# ----------------------------------------
class ScalesCategory(BaseModel):
    '''
    Class representing a group of signal/background scales
    '''
    trigger    : Trigger
    brem       : Brem
    q2bin      : list[Qsq]
    backgrounds: list[Component]
    signal     : Component
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
    categories       : dict[str,ScalesCategory]
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
    def _tabulate(self, name : str, category : ScalesCategory) -> None:
        '''
        Parameters
        --------------
        name    : Name of category
        category: Config to plot a given group of scale factors
        '''
        log.info(f'Tabulating {name}')

        df = pnd.DataFrame(columns = ['Signal', 'Background', 'Value', 'Error'])

        signal = category.signal
        for q2bin in category.q2bin:
            obj = PrecScales(
                output_directory = self._cfg.output_directory,
                trigger          = category.trigger,
                brem             = category.brem,
                q2bin            = q2bin)

            for background in category.backgrounds:
                val, err       = obj.get_scale(
                    signal     = category.signal, 
                    background = background)

                log.debug(f'{val:10.3g}{err:10.3g}')

                df.loc[len(df)] = {
                    'Signal'     : signal, 
                    'Background' : background,
                    'Value'      : val,
                    'Error'      : err, 
                }
    # ----------------------------------------
    def run(self) -> None:
        '''
        Runs plotting
        '''
        for name, category in self._cfg.categories.items():
            with Cache.cache_root(path = _ANADIR / 'scales/.cache' ):
                self._tabulate(name = name, category = category)
# ----------------------------------------
