'''
This module holds tests for functions in xroot_eos.py
'''
import pytest

from dmu.fsystem.xroot_eos import XRootEOS
from dmu.logging.log_store import LogStore

# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:xroot_eos', 10)
# ----------------------
@pytest.mark.skip
def test_glob_eos():
    '''
    Tests globbing in EOS
    '''
    host = "root://eoslhcb.cern.ch"
    path = "/eos/lhcb/wg/dpa/wp2/ci/22781/btoxll_mva_2024_nopid"

    obj   = XRootEOS(host = host)
    paths = obj.glob(dir_path = path, ext = 'root')

    assert len(paths) == 168
