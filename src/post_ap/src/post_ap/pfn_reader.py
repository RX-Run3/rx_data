'''
Module storing PFNReader class
'''
import apd

from bitmath   import GB
from functools import cached_property
from typing    import Literal
from pydantic  import BaseModel, RootModel
from pydantic  import ConfigDict 
from apd       import SampleCollection
from dmu       import LogStore
from .types    import Production

log = LogStore.add_logger('post_ap:pfn_reader')
# ---------------------------------------
class Sample(BaseModel):
    '''
    Class meant to represet a set of MC samples
    '''
    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        frozen                  = False)

    data    : SampleCollection
    name    : str
    version : str
    # ------------------------------
    def sample_size(self) -> GB:
        '''
        Sample size in GB
        '''
        value = self.data.byte_count()
        size  = int(value / 1000_000_000)

        return GB(size)
    # ------------------------------
    def __str__(self) -> str:
        value  = '\n'
        value += 40 * '-' + '\n'
        value += f'{"Name     ":<20}{self.name:<40}\n'
        value += f'{"Version  ":<20}{self.version:<10}\n'
        value += f'{"nFiles   ":<20}{self.size:<10}\n'
        value += f'{"Size [GB]":<20}{self.sample_size():<10}\n'
        value += 40 * '-' + '\n'
        for pfn in self.pfns[:20]:
            value += f'{pfn}\n'
        value += ''

        return value
    # ------------------------------
    def sample_string(self) -> str:
        '''
        String describing sample. Meant to be called by
        __str__ of Samples
        '''
        return f'{self.name:<40}{self.version:<10}{self.size:<10}\n'
    # ------------------------------
    @cached_property
    def size(self) -> int:
        '''
        Number of ntuples in sample
        '''
        return len(self.lfns)
    # ------------------------------
    @cached_property
    def lfns(self) -> list[str]:
        '''
        List of LFNs
        '''
        return self.data.LFNs()
    # ------------------------------
    @cached_property
    def pfns(self) -> list[str]:
        '''
        List of PFNs
        '''
        return self.data.PFNs()
# ---------------------------------------
class Samples(RootModel[list[Sample]]):
    '''
    Class meant to represet a set of MC samples
    '''
    # -------------------------
    def __str__(self) -> str:
        value = '\n' + 60 * '-' + '\n'
        value+= f'{"Name":<40}{"Version":<10}{"Size":<10}\n'
        value+= 60 * '-' + '\n'
        for sample in self.root:
            value += sample.sample_string()
        value+= 60 * '-'

        return value
    # -------------------------
    @cached_property
    def size(self) -> int:
        return len(self.root)
    # -------------------------
    @cached_property
    def pfns(self) -> list[str]:
        '''
        List of PFNs in all samples
        '''
        value : list[str] = []

        for sample in self.root:
            value += sample.pfns

        return value
    # -------------------------
    @cached_property
    def lfns(self) -> list[str]:
        '''
        List of LFNs in all samples
        '''
        value : list[str] = []

        for sample in self.root:
            value += sample.lfns

        return value
# ---------------------------------------
class ProductionConf(BaseModel):
    '''
    Class representing configuration for analysis production

    Attributes
    ----------------
    versions: Map from group of samples to version, e.g. 'data_turbo_24c1 : v1r1670'
    samples : Dictionary with 
        key  : Name of group of samples, e.g. `data_turbo_24c1`
        value: List of samples as shown in AP, e.g.
            - data_24_magdown_turbo_24c2
            - data_24_magup_turbo_24c2
    '''
    versions : dict[str,str]
    samples  : dict[str,list[str]]
# ---------------------------------------
class PFNReaderConf(BaseModel):
    '''
    Class used to configure PFNReader
    '''
    working_group : Literal['rd']
    productions   : dict[Production,ProductionConf]
# ---------------------------------------
class PFNReader:
    '''
    Thin wrapper around apd used to get list of PFNs
    '''
    #------------------------------------
    def __init__(self, cfg : PFNReaderConf):
        '''
        cfg: Dictionary with configuration needed to read PFNs
        '''
        self._cfg = cfg
    #------------------------------------
    def _samples_from_collection(
        self, 
        collection : SampleCollection, 
        l_sample   : list[str], 
        version    : str) -> Samples:
        '''
        Parameters
        ---------------
        collection: APD object representing set of samples
        l_sample  : Sample names targetted
        version   : version targetted
        '''
        samples : list[Sample] = []
        for sample in collection:
            name = sample['name'   ]
            vers = sample['version']

            if vers != version:
                continue

            if name not in l_sample:
                continue

            sam = collection.filter(name=name, version = vers)
            elm = Sample(
                name    = name,
                version = vers,
                data    = sam)

            samples.append(elm)

        return Samples(root = samples)
    # ---------------------------------------
    def get_samples(
        self, 
        production : Production, 
        nickname   : str) -> Samples:
        '''
        Parameters
        -------------------
        production : Name of AP production, e.g. rd_ap_2024
        nickname   : Used to denote list of samples in config, e.g. data

        Returns
        -------------------
        Object representing set of samples
        '''
        wg         = self._cfg.working_group
        apo        = apd.get_analysis_data(analysis=production, working_group=wg)
        collection = apo.all_samples()
        if not isinstance(collection, SampleCollection):
            raise ValueError('Cannot retrieve a collection of samples for {production}:{nickname}')

        l_sample   = self._cfg.productions[production].samples[nickname]
        version    = self._cfg.productions[production].versions[nickname]

        log.info('Using samples from:')
        for sample in l_sample:
            log.info(f'  {production}:{version}/{sample}')

        samples        = self._samples_from_collection(
            collection = collection, 
            l_sample   = l_sample, 
            version    = version)

        log.info(f'Found {samples.size} samples')

        return samples 
# ---------------------------------------
