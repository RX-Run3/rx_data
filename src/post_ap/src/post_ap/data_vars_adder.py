'''
Module containing DataVarsAdder class
'''
from importlib.resources import files

import yaml
import numpy

from ROOT import RDataFrame, Numba

from dmu.logging.log_store import LogStore

log = LogStore.add_logger('post_ap:data_vars_adder')
# -------------------------------------
def _get_good_runs() -> tuple[numpy.ndarray, numpy.ndarray]:
    runs_path = files('post_ap_data').joinpath('selection/good_runs.yaml')
    runs_path = str(runs_path)
    with open(runs_path, encoding='utf-8') as ifile:
        l_runs = yaml.safe_load(ifile)

    l_low = []
    l_hig = []
    for l_run in l_runs:
        low_run = l_run[0]
        if   len(l_run) == 1:
            hig_run = l_run[0]
        elif len(l_run) == 2:
            hig_run = l_run[1]
        else:
            raise ValueError(f'Found invalid run range: {l_run}')

        l_low.append(low_run)
        l_hig.append(hig_run)

    arr_low = numpy.array(l_low)
    arr_hig = numpy.array(l_hig)

    return arr_low, arr_hig

arr_low_run, arr_hig_run = _get_good_runs()
# -------------------------------------
@Numba.Declare(['int', 'int'], 'int')
def get_block(run_number : int, fill_number : int) -> int:
    block_run = 298626 <=  run_number <= 301278
    block_fil = 9808   <= fill_number <= 9910
    if block_run and block_fil:
        return 4

    block_run = 301325 <=  run_number <= 302403
    block_fil = 9911   <= fill_number <= 9943
    if block_run and block_fil:
        return 3

    block_run = 302429 <=  run_number <= 303010
    block_fil = 9945   <= fill_number <= 9978
    if block_run and block_fil:
        return 2

    block_run = 303092 <=  run_number <= 304604
    block_fil = 9982   <= fill_number <= 10056
    if block_run and block_fil:
        return 1

    block_run = 304648 <=  run_number <= 305739
    block_fil = 10059  <= fill_number <= 10102
    if block_run and block_fil:
        return 5

    block_run = 305802 <= run_number  <= 307544
    block_fil = 10104  <= fill_number <= 10190
    if block_run and block_fil:
        return 6

    block_run = 307576 <= run_number  <= 308098
    block_fil = 10197  <= fill_number <= 10213
    if block_run and block_fil:
        return 7

    block_run = 308104 <= run_number  <= 308540
    block_fil = 10214  <= fill_number <= 10232
    if block_run and block_fil:
        return 8

    return -1
# -------------------------------------
@Numba.Declare(['int'], 'int')
def get_dataq(run_number : int) -> int:
    '''
    Takes run number, returns 0 (bad run) or 1 (good run)
    '''
    for low_run, hig_run in zip(arr_low_run, arr_hig_run, strict=True):
        if low_run <= run_number <= hig_run:
            return 1

    return 0
# -------------------------------------
class DataVarsAdder:
    '''
    Class used to add variables to dataframes that only make sense for data
    It adds:

    - block      : Block number
    - is_good_run: Check for run data quality
    '''
    # -------------------------------------
    def __init__(self, rdf : RDataFrame):
        self._rdf = rdf

        self._l_name : list[str] = []
    # -------------------------------------
    def _add_dataq(self, rdf : RDataFrame, name : str) -> RDataFrame:
        log.info(f'Defining {name}')

        rdf = rdf.Define(name, 'Numba::get_dataq(RUNNUMBER)')
        self._l_name.append(name)

        return rdf
    # -------------------------------------
    def _add_block(self, rdf : RDataFrame, name : str) -> RDataFrame:
        log.info(f'Defining {name}')
        rdf = rdf.Define(name, 'Numba::get_block(RUNNUMBER, FillNumber)')
        self._l_name.append(name)

        return rdf
    # -------------------------------------
    @property
    def names(self) -> list[str]:
        '''
        Returns names of added branches
        '''
        return self._l_name
    # -------------------------------------
    def get_rdf(self) -> RDataFrame:
        '''
        Returns dataframe with all variables added (or booked in this case)
        '''
        rdf = self._rdf
        rdf = self._add_dataq(rdf, 'dataq')
        rdf = self._add_block(rdf, 'block')

        return rdf
# -------------------------------------
