'''
Module with BkkChecker class
'''

import os
import re
import yaml
import subprocess
import pandas                        as pnd
import ap_utilities.decays.utilities as aput

from pathlib                         import Path
from pydantic                        import BaseModel
from typing                          import Final
from concurrent.futures              import ThreadPoolExecutor
from ap_utilities.logging.log_store  import LogStore
from omegaconf                       import DictConfig

log=LogStore.add_logger('ap_utilities:bkk_checker')

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
        cfg  : DictConfig):
        '''
        Parameters
        -------------------
        name     : Name of section, needed to dump output
        d_section: A dictionary representing sections of samples
        '''

        self._suffix = '' if 'suffix' not in cfg else cfg.suffix
        self._name   = name
        self._dry    = False
        self._cfg    = cfg
        self._out_dir= self._get_out_dir()

        self._l_event_type : list[str] = self._get_event_types()
    # -------------------------
    def _get_out_dir(self) -> Path:
        ana_dir = os.environ.get('ANADIR', FALLBACK)
        out_dir = Path(ana_dir) / f'bkk_checker/{self._name}'
        out_dir.mkdir(parents = True, exist_ok = True)

        return out_dir
    # -------------------------
    def _get_event_types(self) -> list[str]:
        l_evt  = self._list_from_dict('evt_type')
        nevt = len(l_evt)
        log.debug(f'Found {nevt} event types')

        l_nick = self._list_from_dict('nickname')
        nnick = len(l_nick)
        log.debug(f'Found {nnick} nicknames')

        l_evt += [ aput.read_event_type(nick) for nick in l_nick ]

        return l_evt
    # -------------------------
    def _list_from_dict(self, key : str) -> list[str]:
        if key not in self._cfg:
            return []

        return self._cfg[key]
    # -------------------------
    def _nfiles_line_from_stdout(self, stdout : str) -> str:
        l_line = stdout.split('\n')
        try:
            [line] = [ line for line in l_line if line.startswith('Nb of Files') ]
        except ValueError:
            log.debug(f'Cannot find number of files in: \n{stdout}')
            return 'None'

        return line
    # -------------------------
    def _nfiles_from_stdout(self, stdout : str, bkk : str) -> int:
        line  = self._nfiles_line_from_stdout(stdout)
        log.debug(f'Searching in line {line}')

        regex = r'Nb of Files      :  (\d+|None)'
        mtch  = re.match(regex, line)

        if not mtch:
            log.debug(f'For BKK: {bkk}')
            log.debug(f'No match found in: \n{stdout}')
            return 0

        nsample = mtch.group(1)
        if nsample == 'None':
            log.debug('Found zero files')
            return 0

        log.debug(f'Found {nsample} files')

        return int(nsample)
    # -------------------------
    def _was_found(self, event_type : str) -> bool:
        '''
        Parameters
        -------------------
        event_type: EventType, e.g. 12153001

        Returns
        -------------------
        True if a sample exist for the event type
        '''
        cfg   = self._cfg.settings
        if cfg.block_id == '2024.W31.34':
            bkk   = f'/MC/{cfg.year}/Beam6800GeV-{cfg.block_id}-{cfg.polarity}-{cfg.nu_path}-25ns-{cfg.generator}/{cfg.sim_vers}/HLT1_2024.W31.34_noUT/HLT2-{cfg.hlt_conf}/{event_type}/HLT2.DST'
        else:
            bkk   = f'/MC/{cfg.year}/Beam6800GeV-{cfg.block_id}-{cfg.polarity}-{cfg.nu_path}-25ns-{cfg.generator}/{cfg.sim_vers}/HLT2-{cfg.hlt_conf}/{event_type}/HLT2.DST'

        log.info(f'{"":<4}{bkk:<100}')

        found = self._find_bkk(bkk)

        return found
    # -------------------------
    def _find_bkk(self, bkk : str) -> bool:
        '''
        Parameters
        ------------------
        bkk: Bookkeeping path to MC sample

        Returns 
        ------------------
        True if the path was found with at least one file
        It also saves path to text
        '''
        if not self._dry:
            cmd_bkk = ['dirac-bookkeeping-get-stats', '-B' , bkk]
            result  = subprocess.run(cmd_bkk, capture_output=True, text=True, check=False)
            nfile   = self._nfiles_from_stdout(result.stdout, bkk)
            found   = nfile != 0
            stdout  = result.stdout
        else:
            found   = True
            stdout  = SAMPLE_INFO 

        if not found:
            log.error(f'Missing: {bkk}')
            return False

        name =  bkk.replace(r'/', '_')
        name = name.replace(r'.', '_')
        name = name.replace(r'-', '_')
        path =f'{self._out_dir}/{name}.txt'

        log.debug(f'Saving to: {path}')
        with open(path, 'w', encoding='utf-8') as ofile:
            ofile.write(stdout)

        return found
    # -------------------------
    def _get_samples_with_threads(self, nthreads : int) -> list[str]:
        l_found : list[bool] = []
        with ThreadPoolExecutor(max_workers=nthreads) as executor:
            l_result = [ executor.submit(self._was_found, event_type) for event_type in self._l_event_type ]
            l_found  = [result.result() for result in l_result ]

        l_event_type = [ event_type for event_type, found in zip(self._l_event_type, l_found) if found ]

        return l_event_type
    # -------------------------
    def _save_info_yaml(self, l_event_type : list[str]) -> None:
        text = ''
        cfg  = self._cfg.settings
        for evt_type in l_event_type:
            nu_name         = cfg.nu_path.replace('.', 'p')
            nick_name_org   = aput.read_decay_name(evt_type)
            nick_name       = f'"{nick_name_org}{self._suffix}"'
            sim_vers        = f'"{cfg.sim_vers}"'
            text           += f'({nick_name:<60}, "{evt_type}" , "{cfg.block_id}", "{cfg.polarity}"  , "{cfg.ctags}", "{cfg.dtags}", "{cfg.nu_path}", "{nu_name}", {sim_vers:<20}, "{cfg.generator}" ),\n'

        output_path = f'{self._out_dir}/info.yaml'
        log.info(f'Saving to: {output_path}')
        with open(output_path, 'w', encoding='utf-8') as ofile:
            ofile.write(text)
    # -------------------------
    def _save_validation_config(self, l_event_type : list[str]) -> None:
        d_data = {'samples' : {}}
        for event_type in l_event_type:
            nick_name = aput.read_decay_name(event_type)
            d_data['samples'][nick_name] = ['any']

        output_path = f'{self._out_dir}/validation.yaml'
        log.info(f'Saving to: {output_path}')
        with open(output_path, 'w', encoding='utf-8') as ofile:
            yaml.safe_dump(d_data, ofile, width=200)
    # -------------------------
    def save(
        self, 
        nthreads : int  = 1,
        dry      : bool = False) -> pnd.DataFrame:
        '''
        Will check if samples exist in grid
        Will save list of found samples to text file with same name as input YAML, but with txt extension

        Parameters
        ----------------
        nthreads: Number of threads to use for check
        dry     : If True will stop before calling Dirac, default False 
        '''
        self._dry = dry

        log.info('Filtering input')
        if nthreads == 1:
            log.info('Using single thread')
            l_event_type = [ event_type for event_type in self._l_event_type if self._was_found(event_type) ]
        else:
            log.info(f'Using {nthreads} threads')
            l_event_type = self._get_samples_with_threads(nthreads)

        nfound = len(l_event_type)
        npased = len(self._l_event_type)

        log.info(f'Found: {nfound}/{npased}')
        self._save_info_yaml(l_event_type = l_event_type)
        self._save_validation_config(l_event_type = l_event_type)
# ---------------------------------
