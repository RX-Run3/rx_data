'''
Module storing LogInfo class
'''
import os
import re
import glob
import zipfile

from functools                      import lru_cache
from ap_utilities.logging.log_store import LogStore

log = LogStore.add_logger('ap_utilities:log_info')
# ---------------------------------------------
class LogInfo:
    '''
    Class taking a zip file with logging information from AP pipelines
    and extracting information like the number of entries that it ran over
    '''
    # ---------------------------------------------
    def __init__(self, zip_path : str):
        self._zip_path = zip_path
        self._log_wc   = 'DaVinci_*.log'

        self._out_path : str
        self._log_path : str

        self._entries_regex : str = r'\s*\|\s*"#\snon-empty events for field .*"\s*\|\s*(\d+)\s*\|.*'
        self._get_dv_lines        = lru_cache(maxsize=3)(self._get_dv_lines)
    # ---------------------------------------------
    def _get_log_path(self) -> str:
        path_wc = f'{self._out_path}/*/{self._log_wc}'

        try:
            [log_path] = glob.glob(path_wc)
        except ValueError as exc:
            raise FileNotFoundError(f'Cannot find one and only one DaVinci log file in: {path_wc}') from exc

        return log_path
    # ---------------------------------------------
    def _get_dv_lines(self) -> list[str] | None:
        if not os.path.isfile(self._zip_path):
            log.warning(f'Cannot find: {self._zip_path}')
            return None

        with zipfile.ZipFile(self._zip_path, 'r') as zip_ref:
            zip_ref.extractall(self._out_path)

        self._log_path = self._get_log_path()

        with open(self._log_path, encoding='utf-8') as ifile:
            l_line = ifile.read().splitlines()

        return l_line
    # ---------------------------------------------
    def _entries_from_line(self, line : str) -> int | None:
        mtch = re.match(self._entries_regex, line)
        if not mtch:
            log.warning(f'Cannot extract number of entries from line \"{line}\" using regex \"{self._entries_regex}\"')
            return None

        entries = mtch.group(1)

        return int(entries)
    # ---------------------------------------------
    def _all_in_line(self, line : str, l_substr : list[str]) -> bool:
        found = True
        for substr in l_substr:
            found = found and substr in line

        return found
    # ---------------------------------------------
    def _index_at_first_instance(self, l_line : list[str], l_substr : list[str]) -> int | None:
        index = None
        for i_line, line in enumerate(l_line):
            if self._all_in_line(line, l_substr):
                index = i_line
                break

        return index
    # ---------------------------------------------
    def _get_line_with_entries(self, l_line : list[str], alg_name : str) -> str | None:
        algo_index = self._index_at_first_instance(l_line, l_substr=[alg_name, 'Number of counters'])
        if algo_index is None:
            log.warning(f'Cannot find line with \"Number of counters\" and \"{alg_name}\" in {self._log_path}')
            return None

        l_line = l_line[algo_index:]

        atrm_index = self._index_at_first_instance(l_line, l_substr=['ApplicationMgr'])
        if atrm_index is None:
            log.warning('Cannot find line with ApplicationMgr')
            return None

        l_line = l_line[:atrm_index]

        none_index = self._index_at_first_instance(l_line, l_substr=[' | "# non-empty events for field'])
        if none_index is None:
            log.warning('Cannot find line with non empty events line')
            return None

        return l_line[none_index]
    # ---------------------------------------------
    def get_mcdt_entries(self, alg_name : str, fall_back : int = -1) -> int:
        '''
        Returns entries that DaVinci ran over to get MCDecayTree
        '''
        # If not clipped, long names will cause failure
        # due to clipping in logs
        alg_name       = alg_name[:30]
        self._out_path = f'/tmp/log_info/{alg_name}'
        os.makedirs(self._out_path, exist_ok=True)

        l_line            = self._get_dv_lines()
        if l_line is None:
            return fall_back

        line_with_entries = self._get_line_with_entries(l_line, alg_name)
        if line_with_entries is None:
            return fall_back

        nentries          = self._entries_from_line(line_with_entries)
        if nentries is None:
            return fall_back

        log.debug(f'Found {nentries} entries')

        return nentries
# ---------------------------------------------
