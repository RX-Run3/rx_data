'''
Module storing PFNReader class
'''
import apd

from typing    import Literal
from pydantic  import BaseModel
from apd       import SampleCollection
from dmu       import LogStore
from .types    import Production

log = LogStore.add_logger('post_ap:pfn_reader')
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
    def _paths_from_collection(
        self, 
        collection : SampleCollection, 
        l_sample   : list[str], 
        version    : str) -> dict[str,list[str]]:
        d_pfn = {}
        npfn  = 0

        log.debug(80 * '-')
        log.debug(f'{"Sample":<40}{"Version":<20}{"Number of PFNs":<20}')
        log.debug(80 * '-')
        pfn_ex = None
        for d_info in collection:
            sample_name = d_info['name']
            sample_vers = d_info['version']

            if sample_vers != version:
                continue

            if sample_name not in l_sample:
                continue

            sam                = collection.filter(name=sample_name, version = sample_vers)
            l_pfn              = sam.PFNs()
            npfn              += len(l_pfn)
            d_pfn[sample_name] = l_pfn
            pfn_ex             = l_pfn[0]

            log.debug(f'{sample_name:<40}{sample_vers:<20}{len(l_pfn):<80}')

        log.info(f'Found {npfn} PFNs, e.g.: {pfn_ex}')

        return d_pfn
    # ---------------------------------------
    def get_pfns(self, production : str, nickname : str) -> dict[str,list[str]]:
        '''
        Parameters:

        production : Name of AP production, e.g. rd_ap_2024
        nickname   : Used to denote list of samples in config, e.g. data

        Returns:

        Dictionary matching sample name and list of ROOT files
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

        d_path     = self._paths_from_collection(collection, l_sample, version)

        nsamp = len(d_path)
        log.info(f'Found {nsamp} samples')

        return d_path
# ---------------------------------------
