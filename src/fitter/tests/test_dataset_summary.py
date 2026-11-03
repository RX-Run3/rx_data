'''
Module with tests for DatasetSummary class
'''
import pytest

from typing    import Final
from pathlib   import Path
from fitter    import DatasetSummary
from rx_common import Trigger
from dmu       import LogLevels, LogStore

log=LogStore.add_logger('fitter:test_dataset_summary')

_CUTFLOW : Final[str] = '''
|    | cut        |   All |   Passed | Efficiency          |   Cummulative |
|---:|:-----------|------:|---------:|:--------------------|--------------:|
|  0 | truth      |  8784 |     3752 | 0.42714025500910746 |    0.42714    |
|  1 | q2         |  3752 |     3228 | 0.8603411513859275  |    0.367486   |
|  2 | ghost      |  3228 |     3228 | 1.0                 |    0.367486   |
|  3 | hlt1       |  3228 |     3228 | 1.0                 |    0.367486   |
|  4 | hlt2       |  3228 |     3228 | 1.0                 |    0.367486   |
|  5 | kinem_lep  |  3228 |     3200 | 0.9913258983890955  |    0.364299   |
|  6 | kinem_had  |  3200 |     3163 | 0.9884375           |    0.360087   |
|  7 | kst_mass   |  3163 |     1597 | 0.5049004110022131  |    0.181808   |
|  8 | kst_pt     |  1597 |     1597 | 1.0                 |    0.181808   |
|  9 | tr_ipchi2  |  1597 |     1597 | 1.0                 |    0.181808   |
| 10 | pid_l      |  1597 |     1500 | 0.939261114589856   |    0.170765   |
| 11 | pid_k      |  1500 |     1334 | 0.8893333333333333  |    0.151867   |
| 12 | pid_pi     |  1334 |      193 | 0.1446776611694153  |    0.0219718  |
| 13 | rich       |   193 |      193 | 1.0                 |    0.0219718  |
| 14 | acceptance |   193 |      193 | 1.0                 |    0.0219718  |
| 15 | jpsi_misid |   193 |      193 | 1.0                 |    0.0219718  |
| 16 | cascade    |   193 |      118 | 0.6113989637305699  |    0.0134335  |
| 17 | hop        |   118 |      103 | 0.8728813559322034  |    0.0117259  |
| 18 | cmb        |   103 |       82 | 0.7961165048543689  |    0.00933515 |
| 19 | prc        |    82 |       20 | 0.24390243902439024 |    0.00227687 |
| 20 | mass       |    20 |       20 | 1.0                 |    0.00227687 |
| 21 | block      |    20 |        0 | 0.0                 |    0          |
| 22 | brem       |     0 |        0 | <NA>                |  nan          |
'''
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:dataset_summary', LogLevels.debug)
# ----------------------
def test_markdown_to_df(tmp_path : Path):
    path = tmp_path / 'markdown.md'
    path.write_text(_CUTFLOW)

    df = DatasetSummary.markdown_to_df(path = path)

    print(df)
# -------------------------------------
def test_simple():
    '''
    Simplest test
    '''
    dsm = DatasetSummary(
        trigger = Trigger.rkst_ee_os,
        name    = 'reso_dtf-latest-990-600')
    df  = dsm.get_df()

    print(df)
# -------------------------------------
