'''
Module with BkkChecker class
'''

import os
import re
import pandas     as pnd
import subprocess

from pathlib                         import Path
from pydantic                        import BaseModel, RootModel
from typing                          import Final
from concurrent.futures              import ThreadPoolExecutor
from ap_utilities                    import SettingsConf, Block
from ap_utilities.decays             import utilities as aput
from ap_utilities.logging.log_store  import LogStore

FALLBACK    : Final[str] = '/tmp/ap_utilities/output'
SAMPLE_INFO : Final[str] = ''' 
For BK query: {'ConfigName': 'MC', 'ConfigVersion': '2024', 'ConditionDescription': 'Beam6800GeV-2024.W41.42-MagUp-Nu7.6-25ns-Pythia8', 'ProcessingPass': '/Sim10g/HLT2-2024.W40.42', 'EventType': '12113002', 'FileType': 'HLT2.DST', 'Visible': 'Yes', 'SimulationConditions': 'Beam6800GeV-2024.W41.42-MagUp-Nu7.6-25ns-Pythia8'}
Nb of Files      :  51
Nb of Events     :  413'644
Total size       :  286.865 GB (693.5 kB per evt)
Total size (1024):  267.164 GiB (677.3 kiB per evt)
Luminosity       :  0.000 
Size per /pb     :  0.0 GB
'''

log = LogStore.add_logger('ap_utilities:bkk_checker')
# ---------------------------------
class BkkInfo(BaseModel):
    '''
    Class meant to represent information associated to
    MC sample
    '''
    block      : str
    sample     : str
    event_type : int
    sim_vers   : str
    nu_path    : str
    block_id   : str
    polarity   : str
    ctags      : str
    dtags      : str
    generator  : str
    stdout     : str  | None
    # -----------------------------
    nevents    : int  | None = None
    size       : str  | None = None
    found      : bool | None = None
    # --------------------------------
    def model_post_init(self, _) -> None:
        self.size       = self._get_size()
        self.nevents    = self._get_nevents()
        self.found      = self.stdout is not None 
    # --------------------------------
    def _extract_with_regex(self, regex : str, string : str) -> str:
        match = re.search(regex, string)
        if not match:
            log.error(self.stdout)
            raise ValueError(f'Cannot find size with regex: {regex}')

        return match.group(1) 
    # --------------------------------
    def _get_size(self) -> str:
        if self.stdout is None:
            return '0 GB'

        regex = r'Total size\s+:\s+([\d\.]+ GB)'

        return self._extract_with_regex(regex = regex, string = self.stdout)
    # --------------------------------
    def _get_nevents(self) -> int:
        if self.stdout is None:
            return 0 

        regex = r"Nb of Events\s+:\s+([\d']+)"
        val   = self._extract_with_regex(regex = regex, string = self.stdout)
        val   = val.replace("'", '')

        return int(val)
    # --------------------------------
    @property
    def row(self) -> pnd.Series:
        '''
        Data used to build row in dataframe
        This data corresponds to a sample Bkk
        '''
        data = {
            'Size [GB]': self.size,
            'Block'    : self.block,
            'Sample'   : self.sample,
            'EventType': self.event_type,
            'Events'   : self.nevents,
            'Found'    : self.found,
        }

        return pnd.Series(data) 
    # --------------------------------
    @property
    def ap_line(self) -> str:
        '''
        Line meant to represent sample in info.yaml used for AP
        '''
        nu_name   = self.nu_path.replace('.', 'p')
        nick_name = aput.read_decay_name(self.event_type)

        part_1 = f'({nick_name:<60}, "{self.event_type}" , "{self.block_id}", "{self.polarity}"  , "{self.ctags}"'
        part_2 = f'"{self.dtags}", "{self.nu_path}", "{nu_name}", {self.sim_vers:<20}, "{self.generator}" )'

        return f'{part_1}, {part_2},'
# ---------------------------------
class DatasetInfo(RootModel[list[BkkInfo]]):
    def save_info_yaml(self, path : Path) -> None:
        '''
        Merge info instances and save YAML with it
        '''
        yaml_lines = [ info.ap_line for info in self.root ]
        text       = '\n'.join(yaml_lines)

        log.info(f'Saving to: {path}')
        path.write_text(text)
# ---------------------------------
class BkkChecker:
    '''
    Class meant to check if samples exist in Bookkeeping using multithreading.
    This is useful with large lists of samples, due to low performance of Dirac
    '''
    # -------------------------
    def __init__(
        self, 
        name : str, 
        dry  : bool,
        cfg  : SettingsConf):
        '''
        Parameters
        -------------------
        name : Name of section, needed to dump output
        dry  : If true, do everything but query with dirac, use sample string instead
        cfg  : Configuration controlling sample list
        '''
        self._name   = name
        self._dry    = dry 
        self._cfg    = cfg
        self._out_dir= self.__get_out_dir()
    # -------------------------
    def __get_out_dir(self) -> Path:
        ana_dir = os.environ.get('ANADIR', FALLBACK)
        out_dir = Path(ana_dir) / f'bkk_checker/{self._name}'
        out_dir.mkdir(parents = True, exist_ok = True)

        return out_dir
    # -------------------------
    def __get_block_info(self, block : Block) -> list[BkkInfo]:
        '''
        Parameters
        -------------------
        block: E.g. block_1

        Returns
        -------------------
        List of BkkInfo wrapping information on dataset, based on Dirac's stdout
        '''
        samples= self._cfg.root[block].samples
        log.debug(f'Found {len(samples)} samples for block {block}')

        l_info = [ 
            self.__get_block_evt_info(
                block       = block, 
                evt         = evt, 
                sample_name = sample_name) for evt, sample_name in samples.items() ]

        return l_info
    # -------------------------
    def __get_block_evt_info(
        self, 
        block       : Block, 
        sample_name : str,
        evt         : int) -> BkkInfo:
        '''
        Parameters
        ------------------
        block      : E.g. block_1
        sample_name: E.g. latex string identifying sample
        evt        : Event type

        Returns
        ------------------
        BkkInfo wrapping information on dataset, based on Dirac's stdout
        '''
        cfg   = self._cfg.root[block]
        root  = f'/MC/{cfg.year}/Beam6800GeV-{cfg.block_id}-{cfg.polarity}-{cfg.nu_path}-25ns-{cfg.generator}/{cfg.sim_vers}'

        if cfg.block_id == '2024.W31.34':
            bkk   = f'{root}/HLT1_2024.W31.34_noUT/HLT2-{cfg.hlt_conf}/{evt}/HLT2.DST'
        else:
            bkk   = f'{root}/HLT2-{cfg.hlt_conf}/{evt}/HLT2.DST'

        log.info(f'{"":<4}{bkk:<100}')

        if not self._dry:
            cmd_bkk = ['dirac-bookkeeping-get-stats', '-B' , bkk]
            result  = subprocess.run(cmd_bkk, capture_output=True, text=True, check=False)
            stdout  = result.stdout
        else:
            log.warning('Running dry run')
            stdout  = SAMPLE_INFO 

        out_path = self._out_dir / f'{evt}.txt'
        out_path.write_text(stdout)

        info = BkkInfo(
            nu_path    = cfg.nu_path,
            block_id   = cfg.block_id,
            polarity   = cfg.polarity,
            sim_vers   = cfg.sim_vers,
            ctags      = cfg.ctags,
            dtags      = cfg.dtags,
            generator  = cfg.generator,
            event_type = evt,
            sample     = sample_name, 
            block      = block,
            stdout     = stdout)

        return info
    # -------------------------
    def __get_samples_with_threads(self, nthreads : int) -> list[BkkInfo]:
        '''
        Parameters
        ----------------
        nthreads: Number of processes to use to check sample

        Returns
        ----------------
        List of objects with sample metadata
        '''
        with ThreadPoolExecutor(max_workers=nthreads) as executor:
            l_result = [ executor.submit(self.__get_block_info, block) for block in self._cfg.root ]
            l_info   = [ info  for result in l_result for info in result.result() ]

        return l_info
    # -------------------------
    def save(
        self, 
        nthreads : int  = 1) -> pnd.DataFrame:
        '''
        Will check if samples exist in grid
        Will save list of found samples to text file with same name as input YAML, but with txt extension

        Parameters
        ----------------
        nthreads: Number of threads to use for check

        Returns
        ----------------
        Dataframe where each row represents a sample
        '''
        log.info('Filtering input')

        if nthreads == 1:
            log.info('Using single thread')
            nested = [ self.__get_block_info(block = block) for block in self._cfg.root ]
            log.info(f'Found {len(nested)} blocks')

            l_info = [ info for nest in nested for info in nest ]
            log.info(f'Found {len(l_info)} samples')
        else:
            log.info(f'Using {nthreads} threads')
            l_info = self.__get_samples_with_threads(nthreads)

        dsinfo = DatasetInfo(root = l_info)
        dsinfo.save_info_yaml(path = self._out_dir / 'info.yaml')

        rows : list[pnd.Series] = [ info.row for info in l_info ]

        return pnd.DataFrame(rows)
# ---------------------------------
