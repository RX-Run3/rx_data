'''
Tests for RFPrinter class
'''
import os
import pytest

import dmu.testing.utilities as tut
from dmu.rfile.rfprinter import RFPrinter

# -------------------------------------------------
class Data:
    '''
    Class used to store shared data
    '''
    file_path_simple : str
    file_path_fail   : str
# -------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize() -> None:
    Data.file_path_simple = '/tmp/tests/rfprinter/test.root'
    Data.file_path_fail   = '/this/file/does/not/exist.root'

    os.makedirs('/tmp/tests/rfprinter', exist_ok=True)

    rdf = tut.get_rdf(kind='sig', nentries=10)
    rdf.Snapshot('tree', Data.file_path_simple)
# -------------------------------------------------
def test_simple():
    '''
    Test basic printing
    '''
    obj = RFPrinter(path=Data.file_path_simple)
    obj.save(to_screen=True)
# -------------------------------------------------
def test_raise_on_fail():
    '''
    Test raise_on_fail flag
    '''
    with pytest.raises(FileNotFoundError):
        obj = RFPrinter(path=Data.file_path_fail)
        obj.save(raise_on_fail= True)
# -------------------------------------------------
def test_file_name():
    '''
    Test specifying summary file name
    '''

    obj = RFPrinter(path=Data.file_path_simple)
    obj.save(file_name='summary.txt')
