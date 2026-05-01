'''
Module storing PFNReader class
'''
import apd

from functools import cached_property
from typing    import Final, Literal
from typing    import overload
from pydantic  import BaseModel, RootModel
from pydantic  import ConfigDict 
from apd       import SampleCollection
from dmu       import LogStore
from .types    import Production

log = LogStore.add_logger('post_ap:pfn_reader')

_SECTION : Final[str] = '''
{sample}_filter:
input :
  wg      : {wg} 
  analysis: {analysis} 
  tags:
    version : {version} 
    name    : {sample}_tuple
recipe:
  name       : filter-trees
  entrypoint : rx_filter.main:main
output    : {short_name}.root
'''
# ---------------------------------------
class Sample(BaseModel):
    '''
    Class meant to represet a set of MC samples

    The schema is:

    {'wg': 'rd', 
     'analysis': 'rx_2024', 
     'version': 'v1r5811', 
     'name': 'mc_24_w41_42_magup_sim10g_12153001_bu_jpsik_ee_eq_dpc_tuple', 
     'request_id': 204973, 
     'sample_id': 77484, 
     'state': 'ready', 
     'owners': [], 
     'lfns': {
        '/lhcb/MC/2024/TUPLE.ROOT/00380611/0000/00380611_00000001_1.tuple.root': 
            ['root://eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00380611/0000/00380611_00000001_1.tuple.root']}, 
        'available_bytes'  : 330983170, 
        'total_bytes'      : 330983170, 
        'last_state_update': '2026-04-29T05:23:13', 
        'validity_start'   : '2026-04-28T19:06:41', 
        'validity_end'     : None}

    And the fields can be accessed from data.info
    '''
    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        frozen                  = False)

    data    : SampleCollection
    name    : str
    version : str
    # ------------------------------
    @property
    def info(self) -> str:
        '''
        Object representing section in info.yaml associated
        to this sample and needed to filter it
        '''
        fields = {
            'short_name' : self.short_name,
            'analysis'   : self.analysis,
            'version'    : self.version,
            'sample'     : self.sample,
            'wg'         : self.wg,
        }

        return _SECTION.format(**fields) 
    @cached_property
    def sample_size(self) -> float:
        '''
        Sample size in GB
        '''
        value = self.data.byte_count()
        size  = value / 1000_000_000

        return size
    # ------------------------------
    def __str__(self) -> str:
        value  = '\n'
        value += 40 * '-' + '\n'
        value += f'{"Name     ":<20}{self.name:<40}\n'
        value += f'{"Version  ":<20}{self.version:<10}\n'
        value += f'{"nFiles   ":<20}{self.nfiles:<10}\n'
        value += f'{"Size [GB]":<20}{self.sample_size:<10.3f}\n'
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
        size = self.sample_size
        val  = f'{self.name:<100}{self.version:<10}{self.nfiles:<10}{size:<10.3f}'

        return val
    # ------------------------------
    @cached_property
    def nfiles(self) -> int:
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
        lines : list[str] = []
        for sample in self.root:
            lines.append(sample.sample_string())

        lines.sort()

        value = '\n' + 130 * '-' + '\n'
        value+= f'{"Name":<100}{"Version":<10}{"Files":<10}{"Size [GB]":<10}\n'
        value+= 130 * '-' + '\n'
        value+= '\n'.join(lines)
        value+= '\n' + 130 * '-' + '\n'
        value+= f'Total [GB]: {self.total_size:.3f}\n'
        value+= 130 * '-' + '\n'

        return value
    # -------------------------
    def __iter__(self): # pyright: ignore[reportIncompatibleMethodOverride]
        return iter(self.root) 
    # -------------------------
    @overload
    def __getitem__(self, item: int) -> Sample: ...
    @overload
    def __getitem__(self, item: slice) -> list[Sample]: ...
    def __getitem__(self, item: int | slice) -> Sample | list[Sample]:
        return self.root[item]
    # -------------------------
    @cached_property
    def total_size(self) -> float:
        '''
        Size of all samples in GB
        '''
        sizes = [ sample.sample_size for sample in self.root ]

        return sum(sizes) 
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
        value: Either:
            - List of samples as shown in AP, e.g.
                - data_24_magdown_turbo_24c2
                - data_24_magup_turbo_24c2
            - None, in which case all the samples would be picked
    '''
    versions : dict[str,str]
    samples  : dict[str,list[str] | None]
# ---------------------------------------
class PFNReaderConf(BaseModel):
    '''
    Class used to configure PFNReader
    '''
    working_group : Literal['RD']
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
        l_sample   : list[str] | None, 
        version    : str) -> Samples:
        '''
        Parameters
        ---------------
        collection: APD object representing set of samples
        l_sample  : Sample names targetted or None if one wants all samples
        version   : version targetted
        '''
        samples : list[Sample] = []
        for sample in collection:
            name = sample['name'   ]
            vers = sample['version']

            if vers != version:
                continue

            if l_sample and name not in l_sample:
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

        if l_sample is None:
            log.info(f'Using all samples for version: {version}')
        else:
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
