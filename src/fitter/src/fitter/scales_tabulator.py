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
from .prec_scales   import PrecScales

log = LogStore.add_logger('fitter:scales_tabulator')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
_Q2LABEL: Final[str]  = r'$q^2$ bin' # Label used for q2bin column
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
    @property
    def group(self) -> str:
        '''
        Identifier for group that this category belongs to 
        '''
        q2bins            = '-'.join(self.q2bin)
        no_channel_signal = self.signal.replace('ee', '').replace('mm', '')

        return f'{q2bins}_{no_channel_signal}_{self.trigger.project}'
    # ------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data : dict[str,str]):
        brem = data['brem']
        val  = Brem.from_str(brem)

        data['brem'] = str(val)

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
    def _validate(cls, data : dict[str,str]):
        out_dir = data['output_directory']
        out_dir = _ANADIR / out_dir
        data['output_directory'] = str(out_dir)

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
    def _get_df(self, name : str, category : ScalesCategory) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        name    : Name of category
        category: Config to plot a given group of scale factors

        Returns
        --------------
        Dataframe with values and errors of scales for different backgrounds
        '''
        log.info(f'Tabulating {name}')

        df = pnd.DataFrame(columns = ['Background', 'Value', 'Error', 'Brem', _Q2LABEL])
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
                    'Brem'       : category.brem.latex,
                    '$q^2$ bin'  : q2bin.latex,
                }

        return df
    # ----------------------------------------
    def _get_tex_df(self, name : str, category : ScalesCategory) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        name    : Name of category
        category: Config to plot a given group of scale factors

        Returns
        --------------
        Pandas dataframe with values and errors for scales
        '''
        def _sample_to_tex(sample : str) -> str:
            return Component(sample).latex

        def _scale_to_percent(value : float) -> float:
            return value * 100

        df         = self._get_df(name = name, category = category)
        df_for_tex = df.assign(Background=df['Background'].apply(_sample_to_tex))
        df_for_tex = df_for_tex.assign(Value=df_for_tex['Value'].apply(_scale_to_percent))
        df_for_tex = df_for_tex.assign(Error=df_for_tex['Error'].apply(_scale_to_percent))

        return df_for_tex
    # ----------------------------------------
    def __save_group(self, name : str, dfs : list[pnd.DataFrame]) -> None:
        '''
        Parameters
        ---------------
        name: Name of group
        dfs : List of dataframes in group
        '''
        df   = pnd.concat(dfs)
        path = self._cfg.output_directory / f'{name}.tex'
        log.info(f'Saving to: {path}')

        put.df_to_tex(
            df        = df, 
            path      = path, 
            hide_index=True, 
            d_format  ={'Background' : '{}', 'Value' : '{:.3g}', 'Error' : '{:.3g}'})
    # ----------------------------------------
    def run(self) -> None:
        '''
        Runs plotting
        '''
        dataframes : dict[str,list[pnd.DataFrame]] = dict()

        for name, category in self._cfg.categories.items():
            with Cache.cache_root(path = _ANADIR / 'scales/.cache' ):
                df = self._get_tex_df(name = name, category = category)

            group = category.group
            if group not in dataframes:
                dataframes[group] = [df]
            else:
                dataframes[group].append(df)

        for group, l_df in dataframes.items():
            self.__save_group(name = group, dfs = l_df)
# ----------------------------------------
