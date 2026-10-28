'''
Module storing PFNReader class
'''
import re
import os
import apd

from datetime  import datetime
from ROOT      import TFile
from pathlib   import Path
from functools import cached_property
from typing    import Final, Literal
from typing    import overload, Self
from pydantic  import BaseModel, RootModel, model_validator
from pydantic  import ConfigDict
from apd       import SampleCollection

from dmu         import LogStore
from dmu.generic import hashing
from rx_common   import Component, Trigger
from .types      import Production

log = LogStore.add_logger('post_ap:pfn_reader')

_MAX_JOB_LENGTH    : Final[int] = 84
_MAX_OUTPUT_LENGHT : Final[int] = 50
_DATA_REGEX        : Final[str] = r'data_(24|25)_(magup|magdown)_turbo_rd_(\1c\d)' # Regex for name of data sample jobs
_SIM_REGEX         : Final[str] = r'mc_.*(w\d{2}(_\d{2})?)_.*(\d{8}).*'            # Regex for name of simulated sample jobs 
_SECTION           : Final[str] = '''
{filter_job_name}:
  input :{sample_frac}
    wg              : {wg}
    analysis        : {analysis}
    tags:
      version : {version}
      name    : {ntuple_job_name}
  recipe:
    name      : filter-trees
    entrypoint: rx_filter.main:main
    extra_args:
      - '--project=PROJECT'
      - '--job_name={ntuple_job_name}'
      - '--max_entries=MAX_ENTRIES'
  output: {output_name}
'''
_FRACTION : Final[str] = '''
    sample_fraction : {fraction}
    sample_seed     : "42"'''
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

    Attributes
    ----------------
    storage: Path to directory containing versioned directory containing
             downloaded ntuples, i.e.

             {storage}/v1r5811/ntuple.root
    ''' 
    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        frozen                  = False)

    group   : str
    data    : SampleCollection
    name    : str
    version : str
    storage : Path
    fraction: float | None
    # ------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Sample':
        good_name_length = len(self.name) < _MAX_JOB_LENGTH

        if not good_name_length:
            raise ValueError(f'Job name length is larger than {_MAX_JOB_LENGTH}')

        is_mc   = re.match(_SIM_REGEX , self.name)
        is_data = re.match(_DATA_REGEX, self.name)

        if not is_mc and not is_data:
            raise ValueError(f'Sample {self.name} is neither data nor MC')

        return self
    # ------------------------------
    @cached_property
    def is_mc(self) -> bool:
        return self.name.startswith('mc_')
    # ------------------------------
    @property
    def info(self) -> str:
        '''
        Object representing section in info.yaml associated
        to this sample and needed to filter it
        '''
        if self.fraction is None:
            sample_frac = ''
        else:
            sample_frac = _FRACTION.format(fraction = self.fraction)

        fields = {
            'filter_job_name' : self.name,
            'ntuple_job_name' : self.name,
            'sample_frac'     : sample_frac,
            'output_name'     : self.output_name,
            'analysis'        : self.analysis,
            'version'         : self.version,
            'group'           : self.group,
            'wg'              : self.wg,
        }

        return _SECTION.format(**fields)
    # ------------------------------
    @cached_property
    def event_type(self) -> int:
        '''
        EventType used for MC samples
        For data this will raise ValueError
        '''
        if not self.is_mc:
            raise ValueError(f'Event type not defined for: {self.name}')

        tags = list(self.data.itertags())

        return tags[0]['eventtype']
    # ------------------------------
    @cached_property
    def polarity(self) -> int:
        tags = list(self.data.itertags())

        return tags[0]['polarity']
    # ------------------------------
    @cached_property
    def output_name(self) -> str:
        value = f'{self.group}.root'
        length= len(value)

        if length > _MAX_OUTPUT_LENGHT:
            raise ValueError(f'Output went beyond {_MAX_OUTPUT_LENGHT} (> {length}) limit: {value}')

        return value
    # ------------------------------
    @cached_property
    def block_identifier(self) -> str:
        '''
        E.g. w31, only valid for MC
        '''
        if not self.is_mc:
            raise ValueError(f'Cannot extract block information from: {self.name}')

        mtch = re.match(_SIM_REGEX, self.name)
        if not mtch:
            raise ValueError(f'Cannot extract block identifier from: {self.name}')

        return mtch.group(1)
    # ---------------------------
    @cached_property
    def block(self) -> int:
        '''
        Associations taken from:

        https://lhcb-simulation.web.cern.ch/WPP/MCsamples.html#samples
        '''
        log.debug('Picking up blocks')

        if self.block_identifier ==    'w31':
            return 1

        if self.block_identifier == 'w32_34':
            return 2

        if self.block_identifier == 'w25_27':
            return 4

        if self.block_identifier == 'w35_37':
            return 5

        if self.block_identifier == 'w37_39':
            return 6

        if self.block_identifier == 'w40_41':
            return 7

        if self.block_identifier == 'w41_42':
            return 8

        raise ValueError(f'Cannot find one a block for sample: {self.name}')
    # ------------------------------
    @cached_property
    def analysis(self) -> str:
        '''
        E.g. rx_2024
        '''
        return self.data.info[0]['analysis']
    # ------------------------------
    @cached_property
    def wg(self) -> str:
        return self.data.info[0]['wg'].upper()
    # ------------------------------
    @cached_property
    def sample(self) -> str:
        '''
        Nickname of simulated sample
        '''
        if not self.is_mc:
            raise ValueError(f'MC sample not available for data: {self.name}')

        mtch = re.match(_SIM_REGEX, self.name)
        if not mtch:
            raise ValueError(f'Cannot extract sample name from: {self.name}')

        return mtch.group(1)
    # ------------------------------
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

        for path in self.paths[:20]:
            value += f'{path}\n'
        value += ''

        return value
    # ------------------------------
    def __lt__(self, other) -> bool:
        return self.name < other.name
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
    def local_paths(
        self, 
        must_exist: bool) -> list[Path]:
        '''
        Parameters
        --------------
        must_exist: If True will raise exception if it does not exist

        Returns
        --------------
        Paths in local directory where this sample's files would go
        '''
        paths = [ self.storage / self.version / os.path.basename(pfn) for pfn in self.pfns ]
        if not must_exist:
            return paths

        fail = False
        for path in paths:
            if not path.exists():
                log.error(f'Missing: {path}')
                fail = True
                continue

            if self._fail_check(path = path):
                log.error(f'Corrupted: {path}')
                fail = True

        if fail:
            raise ValueError('At least one path was not found')

        return paths
    # ------------------------------
    def _fail_check(self, path : Path) -> bool:
        '''
        Parameters
        --------------
        path: Path to ROOT file

        Returns
        --------------
        True if file is corrupted
        '''
        ifile = TFile.Open(str(path))

        if not ifile:
            return True

        if ifile.IsZombie():
            ifile.Close()
            return True

        if ifile.TestBit(TFile.kRecovered):
            ifile.Close()
            return True

        ifile.Close()

        return False
    # ------------------------------
    @cached_property
    def paths(self) -> list[Path]:
        '''
        List of paths to ROOT files
        '''
        if not self.storage:
            raise ValueError('Storage location was not set')

        return self.local_paths(must_exist=False)
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
    # ------------------------------
    def _triggers_from_path(self, path : Path | str) -> set[Trigger]:
        '''
        Parameters
        ----------------
        path: Location of ROOT file

        Returns
        ----------------
        Set of strings with HLT2 triggers
        '''
        ifile = TFile.Open(str(path))
        keys  = ifile.GetListOfKeys()

        triggers : set[Trigger] = set()
        for key in keys:
            name = key.GetName()
            if not name.startswith('Hlt2'):
                continue

            trigger = Trigger.from_name(name = name)
            triggers.add(trigger)

        ifile.Close()

        return triggers
    # ------------------------------
    @cached_property
    def hash(self) -> str:
        '''
        Hash, created using sample name
        '''
        return hashing.hash_object([self.name])
    # ------------------------------
    @cached_property
    def triggers(self) -> list[Trigger]:
        '''
        Triggers associated to current sample
        '''
        triggers : set[Trigger] = set()
        for path in self.pfns[:10]:
            # In case one of the files does not get any entry
            # for a trigger, pick triggers in any of 10 files
            triggers = triggers | self._triggers_from_path(path = path)

        log.debug('Found triggers:')
        trigger_list = sorted(list(triggers))
        for trigger in trigger_list:
            log.debug(f'   {trigger}')

        return trigger_list
    # ------------------------------
    @cached_property
    def year_period(self) -> tuple[str,str]:
        '''
        E.g. 24, 24c3 
        '''
        if self.is_mc:
            raise NotImplementedError('Year not implemented for MC')

        mtch = re.match(_DATA_REGEX, self.name)
        if not mtch:
            raise ValueError(f'Invalid data sample name: {self.name}')

        log.debug(f'Found periods {mtch.groups()} in {self.name}')

        return mtch.group(1), mtch.group(3)
    # ------------------------------
    @cached_property
    def year(self) -> str:
        val, _ = self.year_period

        return val 
    # ------------------------------
    @cached_property
    def period(self) -> str:
        _, val = self.year_period

        return val 
    # ------------------------------
    @cached_property
    def target_paths(self) -> dict[Trigger,Path]:
        '''
        Returns
        --------------
        Dictionary mapping Hlt2 trigger to ntuple path associated to it
        The paths are meant to be named as:

        DATA: data_24_magup_24c2_Hlt2RD_BuToKpEE_MVA_misid.root
        MC:   mc_magup_15454101_lb_jpsix_ee_eq_jpsiinacc_Hlt2RD_BuToKpEE_MVA_b9f112a35b.root
        '''
        ana_dir                     = Path(os.environ['ANADIR'])
        paths : dict[Trigger, Path] = {}
        for trigger in self.triggers:
            target_path = ana_dir / f'Data/{trigger.project}/main'

            if self.is_mc:
                component   = Component.from_event_type(etype = self.event_type)
                sample      = component.sample.lower()
                file_name   = f'mc_{self.polarity}_{self.event_type}_{sample}_{trigger}_{self.hash}.root'
            else:
                file_name   = f'data_{self.year}_{self.polarity}_{self.period}_{trigger}.root'

            target_path = target_path / f'latest/{file_name}'

            log.debug(f'Target path: {target_path}')
            paths[trigger] = target_path

        return paths 
    # ------------------------------
    @cached_property
    def targets_date(self) -> datetime | None:
        '''
        Earliest date of targets.
        If any target is missing will return None
        '''
        dates : set[datetime] = set()
        for target in self.target_paths.values():
            if not target.exists():
                return None

            date = self._path_to_date(path = target)

            dates.add(date)

        return min(dates)
    # ------------------------------
    @cached_property
    def downloads_date(self) -> datetime:
        '''
        Latest modification date for downloaded files associated
        to this sample. Will raise exception if any file was not downloaded
        '''
        paths = self.local_paths(must_exist = True)
        dates = [ self._path_to_date(path = path) for path in paths ]

        return max(dates)
    # ------------------------------
    def _path_to_date(self, path : Path) -> datetime:
        '''
        Parameters
        ----------------
        path: Path to file

        Returns
        ----------------
        Modification date of path
        '''
        mtime = path.stat().st_mtime
        date  = datetime.fromtimestamp(mtime)

        return date
    # ------------------------------
    @property
    def is_organized(self) -> bool:
        '''
        Parameters
        -------------
        triggers: List of triggers associated to ROOT files belonging to this sample

        Returns
        -------------
        True if all of the files exist
        '''
        if self.targets_date is None:
            return False

        return self.targets_date > self.downloads_date
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
    # -----------------
    def __len__(self) -> int:
        return self.size 
    # -------------------------
    def __lt__(self, other : Sample) -> bool:
        return self < other
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
    def event_types(self) -> list[int]:
        '''
        List of sorted event types
        '''
        etypes = { sample.event_type for sample in self }

        return sorted(list(etypes))
    # -------------------------
    @cached_property
    def pfns(self) -> set[str]:
        '''
        List of PFNs in all samples
        '''
        value : list[str] = []

        for sample in self.root:
            value += sample.pfns

        return set(value)
    # -------------------------
    @cached_property
    def lfns(self) -> set[str]:
        '''
        List of LFNs in all samples
        '''
        value : list[str] = []

        for sample in self.root:
            value += sample.lfns

        return set(value)
# ---------------------------------------
class ProductionConf(BaseModel):
    '''
    Class representing configuration for analysis production

    Attributes
    ----------------
    versions: Map from group of samples to version, e.g. 'ss_sata : v1r1670'
    samples : Dictionary with
        key  : Name of group of samples, e.g. `ss_data`
        value: Either:
            - List of samples as shown in AP, e.g.
                - data_24_magdown_turbo_24c2
                - data_24_magup_turbo_24c2
            - None, in which case all the samples would be picked
    fractions: Dictionary with:
        Key  : AP job name
        Value: Fraction of data to pick
    '''
    versions : dict[str,str]
    samples  : dict[str,list[str] | None]
    fractions: dict[str,float | None]
    # -----------------------
    @model_validator(mode = 'after')
    def _validate(self) -> Self:
        fail = False
        for fraction in self.fractions.values():
            if fraction is None:
                continue

            if 0 < fraction <= 1.0:
                continue

            fail = True

        if not fail:
            return self

        raise ValueError('At least one fraction has the wrong value')
    # -----------------------
    def __str__(self) -> str:
        return self.model_dump_json(indent = 2)
# ---------------------------------------
class PFNReaderConf(BaseModel):
    '''
    Class used to configure PFNReader
    '''
    working_group : Literal['RD']
    productions   : dict[Production,ProductionConf]
    # ----------------
    def get_data(
        self, 
        kind       : str, 
        production : Production, 
        group      : str):
        '''
        Parameters
        ---------------
        kind      : Type of field e.g. samples, version
        production: E.g. rx_2024, rx_filter 
        group     : Group of samples e.g. mc-rkst
        '''
        if production not in self.productions:
            log.error(self)
            raise ValueError(f'Production {production} not found')

        cfg_prod = self.productions[production]

        if not hasattr(cfg_prod, kind):
            log.error(self)
            raise ValueError(f'Production configuration has no field named {kind}')

        field = getattr(cfg_prod, kind)
        if group not in field:
            log.error(self)
            raise ValueError(f'Cannot find {group}')

        return field[group]
    # ----------------
    def __str__(self) -> str:
        return self.model_dump_json(indent = 3)
# ---------------------------------------
class PFNReader:
    '''
    Thin wrapper around apd used to get list of PFNs
    '''
    #------------------------------------
    def __init__(
        self, 
        storage: Path,
        cfg    : PFNReaderConf):
        '''
        cfg    : Dictionary with configuration needed to read PFNs
        storage: Path to directory containing versioned directory containing
                 downloaded ntuples, i.e.

                 {storage}/v1r5811/ntuple.root
        '''
        self._cfg     = cfg
        self._storage = storage
    #------------------------------------
    def _samples_from_collection(
        self,
        nickname   : str,
        production : Production,
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
                log.debug(f'Skipping version: {vers} != {version}')
                continue

            if l_sample and name not in l_sample:
                log.debug(f'Skipping sample: {name}')
                continue

            cfg_prod = self._cfg.productions[production]
            frac = cfg_prod.fractions.get(name, None)

            sam = collection.filter(name=name, version = vers)
            nsam = len(sam)
            if nsam != 1:
                raise ValueError(f'Expected one sample, found: {nsam}')

            elm = Sample(
                storage = self._storage,
                group   = nickname,
                fraction= frac,
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

        l_sample   = self._cfg.get_data('samples' , production, nickname)
        version    = self._cfg.get_data('versions', production, nickname)

        if l_sample is None:
            log.info(f'Using all samples for version: {version}')
        else:
            log.info('Using samples from:')
            for sample in l_sample:
                log.info(f'  {production}:{version}/{sample}')

        samples        = self._samples_from_collection(
            nickname   = nickname,
            production = production,
            collection = collection,
            l_sample   = l_sample,
            version    = version)

        log.info(f'Found {samples.size} samples for {nickname} in {production}')
        for sample in samples[:20]:
            log.info(f'    {sample.name}')
        log.info('...')

        return Samples(root = sorted(samples))
# ---------------------------------------
