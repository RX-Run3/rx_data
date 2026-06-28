'''
Module containing ScalesTabulator
'''
import os
import pandas as pnd
 
from dmu.workflow   import Cache
from pathlib        import Path
from typing         import Final
from dmu            import LogStore
from pydantic       import BaseModel, model_validator
from dmu.pdataframe import utilities as put
from dmu.generic    import utilities as gut
from rx_common      import Brem, Component, Qsq, Trigger
from fitter         import PrecScales

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
        LogStore.set_level('rx_selection:selection'               , 30)
        LogStore.set_level('rx_efficiencies:efficiency_calculator', 30)

        self._cfg = cfg
    # ----------------------------------------
    def _get_df(self, name : str, category : ScalesCategory) -> tuple[pnd.DataFrame, Component]:
        '''
        Parameters
        --------------
        name    : Name of category
        category: Config to plot a given group of scale factors

        Returns
        --------------
        Tuple with:

        Dataframe with values and errors of scales for different backgrounds
        Signal component with respect to which the scales are calculated 
        '''
        log.info(f'Tabulating {name}')

        df = pnd.DataFrame(columns = ['Background', 'Value', 'Error', '$q^2$ bin'])
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
                    'Background' : background,
                    'Value'      : val,
                    'Error'      : err, 
                    '$q^2$ bin'  : q2bin,
                }

        return df, category.signal
    # ----------------------------------------
    def _tabulate(self, name : str, category : ScalesCategory) -> None:
        '''
        Parameters
        --------------
        name    : Name of category
        category: Config to plot a given group of scale factors
        '''
        df, signal = self._get_df(name = name, category = category)
        df_for_tex = df.assign(Background=df['Background'].apply(lambda sample : Component(sample).latex))
        df_for_tex = df_for_tex.assign(Value=df_for_tex['Value'].apply(lambda value : 100 * value))
        df_for_tex = df_for_tex.assign(Error=df_for_tex['Error'].apply(lambda error : 100 * error))

        path = self._cfg.output_directory / f'{name}-{signal.value}.tex'
        log.info(f'Saving to: {path}')

        put.df_to_tex(
            df        = df_for_tex, 
            path      = path, 
            hide_index=True, 
            d_format  ={'Background' : '{}', 'Value' : '{:.3g}', 'Error' : '{:.3g}'})
    # ----------------------------------------
    def run(self) -> None:
        '''
        Runs plotting
        '''
        for name, category in self._cfg.categories.items():
            with Cache.cache_root(path = _ANADIR / 'scales/.cache' ):
                self._tabulate(name = name, category = category)
# ----------------------------------------
