'''
This script tests FilteredStats class
'''

import os
import pytest
import pandas as pnd

from dmu     import LogStore
from rx_data import FilteredStats

pytestmark = pytest.mark.skipif(
    not os.environ.get('USER') == 'acampove',
    reason ='''
    These tests use FilteredStats, which uses GangaInfo,
    which needs sandbox and cannot run in REANA cluster
    ''')

log=LogStore.add_logger('rx_data:test_filtered_stats')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:filtered_stats', 10)
    pnd.set_option('display.max_columns' , None)
    pnd.set_option('display.max_colwidth', None)
    pnd.set_option('display.width'       ,    0)
# ----------------------
def test_simple():
    '''
    Simplest test of class
    '''
    fst = FilteredStats(analysis='rx', versions=[7, 10])
    df  = fst.get_df()

    print(df)
# ----------------------
def test_all_lfns():
    '''
    Search for information for all the LFNs in the JSON files
    '''
    fst = FilteredStats(analysis='rx', versions=[7, 10])
    df  = fst.get_df()

    print(df)
# ----------------------
def test_exists():
    '''
    Test for exists method
    '''
    fst = FilteredStats(analysis='rx', versions=[7, 10])
    assert     fst.exists(event_type='12153001', block='w31_34', polarity='magup')
    assert not fst.exists(event_type='12345678', block='w31_34', polarity='magup')
    assert not fst.exists(event_type='12153001', block='wxx_xx', polarity='magup')
    assert not fst.exists(event_type='12153001', block='w31_34', polarity='magxx')
