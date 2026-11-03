'''
Module containing SampleConfig class
'''
import hashlib

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
class Samples(BaseModel):
    '''
    Class meant to represent group of MC samples

    Attributes
    -------------
    filter  : HLT2 filtering regex
    sampoles: Dictionary mapping event type with sample string, e.g. latex
    '''
    filter  : str | None
    samples : dict[int,str]
    # ----------------------
    @property
    def hash(self) -> str | None:
        '''
        String representing hash needed to form BKK path
        Or None, if no filter was used
        '''
        if self.filter is None:
            return None

        lines    = sorted(self.filter)
        lines    = "\n".join(lines)
        encoded  = lines.encode("utf-8")
        hash_val = hashlib.sha256(encoded)
        digest   = hash_val.hexdigest()
        digest   = digest[:8]
        digest   = digest.upper()

        return digest
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
    samples  : dict[int,str] = {}
    hash     : str | None    = None
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

    Attributes
    ------------------
    Dictionary with:

    Key  : Category, e.g. sim10d, high, etc
    Value: Dictionary with
        key  : EventType
        Value: Sample identifier, e.g. latex
    '''
    root : dict[str,Samples]
# ----------------------
class SampleConfig:
    '''
    Class meant to provide configuration object needed by BKKChecker

    In practice this config will have the event types (from `analyses/xxx.yaml`)
    merged with the settings (from `samples/xxx.yaml`)
    '''
    # ----------------------
    def __init__(
        self,
        settings : str,
        samples  : str):
        '''
        Parameters
        -------------
        settings: Name of file with simulation configuration, e.g. 2024_sim10g
        samples : Name of file with event types, e.g. by_priority
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
    def get_config(self, category : str) -> SettingsConf:
        '''
        Parameters
        -------------
        category: Names of categories from which event types should be taken

        Returns
        -------------
        Configuration with both samples and settings
        '''
        if category not in self._cfg_sam.root:
            for val in self._cfg_sam.root:
                log.error(val)

            raise ValueError(f'Missing category {category}')

        samples = self._cfg_sam.root[category]

        ntypes  = len(samples.samples)
        if ntypes == 0:
            log.warning(f'Found {ntypes} event types')
        else:
            log.info(f'Found {ntypes} event types')

        for section in self._cfg_set.root.values():
            section.samples = samples.samples
            section.hash    = samples.hash

        return self._cfg_set
# ----------------------
