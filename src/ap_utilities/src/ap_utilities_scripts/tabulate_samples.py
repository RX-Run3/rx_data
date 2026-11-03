'''
Script used to check which MC samples are found in grid
'''
import os
import pandas as pnd

from pathlib        import Path
from dataclasses    import dataclass
from typing         import Final
from rx_common      import Component
from ap_utilities   import LogStore
from ap_utilities   import SampleConfig
from dmu.pdataframe import utilities as put

log=LogStore.add_logger('ap_utilities_scripts:check_bkk_samples')

KINDS       : Final[list[str]] = ['block', 'sample']
SETTINGS    : Final[list[str]] = ['2024_sim10d', '2024_sim10f', '2024_sim10g']
_SAMPLES    : Final[str]       = 'by_priority'
_PRIORITIES : Final[list[str]] = ['high_priority', 'medium_priority', 'low_priority', 'very_low_priority']
_ANADIR     : Final[Path]      = Path(os.environ['ANADIR'])
# --------------------------------
@dataclass(frozen = True)
class MetaData:
    '''
    Class storing sample metadata
    '''
    sim_vers : str
    latex    : str
    evt_type : str
    # --------------------------------
    @property
    def row(self) -> dict[str,str]:
        '''
        Entry as it would be neded for a latex table
        '''
        return {
            'Event Type' : self.evt_type,
            'Decay'      : self.latex,
            'Sim version': self.sim_vers,
        }
    # --------------------------------
    @classmethod
    def from_component(
            cls,
            sim_vers  : str,
            component : Component) -> 'MetaData':
        '''
        Parameters
        --------------
        sim_vers : Version of simulation,e.g. sim10g
        component: Represents sample associated
        '''
        return cls(
            evt_type = component.event_type,
            latex    = component.latex,
            sim_vers = sim_vers)
# --------------------------------
def _get_df(
    config   : str,
    priority : str) -> pnd.DataFrame:
    '''
    Parameters
    -----------------
    config  : Defines configuration used to produce MC, e.g. 2024_sim10d
    priority: Section in `by_priority.yaml` file defining samples, e.g. sim10d

    Returns
    -----------------
    DataFrame associated to samples
    '''
    obj = SampleConfig(
        settings= config,
        samples = _SAMPLES)
    cfg_sam = obj.get_config(category = priority)

    components_metadata : set[MetaData] = set()
    for cfg_block in cfg_sam.root.values():
        for evtnum in cfg_block.samples:
            if not Component.is_valid(arg = evtnum):
                continue

            cmp = Component.from_event_type(evtnum)
            met = MetaData.from_component(
                sim_vers  = cfg_block.sim_vers,
                component = cmp)

            components_metadata.add(met)

    data = [ metadata.row for metadata in components_metadata ]
    df   = pnd.DataFrame(data)

    return df
# --------------------------------
def main():
    '''
    Script starts here
    '''
    dfs : list[pnd.DataFrame] = []

    for priority in _PRIORITIES:
        df = _get_df(
            config   = '2024_sim10d',
            priority = priority)

        dfs.append(df)

    df = _get_df(
        config   = '2024_sim10g',
        priority = 'sim10g')
    dfs.append(df)

    df = pnd.concat(dfs, ignore_index=True)

    is_sim10g    = df['Sim version'] == 'Sim10g'
    is_sim10d    = df['Sim version'] == 'Sim10d'

    sim_g_etypes = df[is_sim10g]['Event Type'].to_list()
    skip_evt     = df['Event Type'].isin(sim_g_etypes)

    flag         = skip_evt & is_sim10d
    df_filt      = df[~flag]
    df_filt.reset_index(drop=True, inplace=True)
    put.df_to_tex(df_filt,
        _ANADIR / 'tables/samples.tex',
        d_format = {},
        caption  = 'Simulation samples used in analysis')
# --------------------------------
if __name__ == '__main__':
    main()
