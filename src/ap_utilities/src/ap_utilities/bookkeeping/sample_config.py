'''
Module containing SampleConfig class
'''
from typing                import Literal
from dmu.generic           import utilities as gut
from dmu.logging.log_store import LogStore
from pydantic              import BaseModel, RootModel

log=LogStore.add_logger('ap_utilities:sample_config')

Block = Literal[
'block_12',
'block_1', 'block_2', 'block_3', 'block_4',
'block_5', 'block_6', 'block_7', 'block_8',
]
# ----------------------
class BlockConf(BaseModel):
    '''
    Class meant to represent block configuration
    '''
    year     : int
    sim_vers : str
    generator: str
    dtags    : str
    block_id : str
    hlt_conf : str
    polarity : Literal['MagUp', 'MagDown']
    nu_path  : str
    ctags    : str
    evt_type : list[int] = []
# ----------------------
class SettingsConf(RootModel):
    '''
    Class meant to represent simulation settings
    '''
    root : dict[Block, BlockConf]
# ----------------------
class SamplesConf(RootModel):
    '''
    Class meant to represent MC samples
    '''
    root : dict[str,dict[int,str]]
# ----------------------
class SampleConfig:
    '''
    Class meant to provide configuration object needed by BKKChecker

    In practice this config will have the event types (from `analyses/xxx.yaml`)
    merged with the settings (from `samples/xxx.yaml`)
    '''
    # ----------------------
    def __init__(self, settings : str, samples : str):
        '''
        Parameters
        -------------
        settings: String describing the name of the file with the simulation configuration, e.g. 2024
        samples : String describinb the name of the file with the event types, e.g. by_priority
        '''
        data       = gut.load_data(
            package= 'ap_utilities_data', 
            fpath  = f'samples/{settings}.yaml')
        data.pop('settings_common', None)

        self._cfg_set = SettingsConf(**data)

        data       = gut.load_data(
            package= 'ap_utilities_data', 
            fpath  = f'analyses/{samples}.yaml')
        data.pop('all', None)

        self._cfg_sam = SamplesConf(root=data)
    # ----------------------
    def get_config(self, categories : list[str]) -> SettingsConf:
        '''
        Parameters
        -------------
        categories: Names of categories from which event types should be taken

        Returns
        -------------
        Configuration with both samples and settings
        '''
        all_event_types = []
        for name, event_types in self._cfg_sam.root.items():
            if name not in categories:
                log.debug(f'Skipping {name}')
                continue

            all_event_types += list(event_types)

        ntypes = len(all_event_types)
        if ntypes == 0:
            log.warning(f'Found {ntypes} event types')
        else:
            log.info(f'Found {ntypes} event types')

        for section in self._cfg_set.root.values():
            section.evt_type = all_event_types

        return self._cfg_set
# ----------------------
