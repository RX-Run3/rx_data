'''
Module will hold unit tests for functions in rdataframe/utilities.py
'''
import math
import numpy
import pytest
import dmu.rdataframe.utilities as ut

from ROOT import RDF, RDataFrame
from dmu  import LogStore

log=LogStore.add_logger('dmu:test:rdataframe:utilities')
# -------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This is called before any test
    '''
    LogStore.set_level('dmu:rdataframe:utilities', 10)
# -------------------------------------------------
@pytest.mark.parametrize('entries', [0, 10])
def test_columns_from_rdf(entries : int):
    '''
    Tests columns_from_rdf
    '''
    rdf = RDataFrame(entries)
    rdf = rdf.Define('a', '1')
    rdf = rdf.Define('b', '2')

    l_col = ut.columns_from_rdf(rdf=rdf)

    assert l_col == ['a', 'b']
    assert all(type(name) is str for name in l_col)
# -------------------------------------------------
@pytest.mark.parametrize('itry', [1, 2])
def test_add_column(itry):
    '''
    Will test adding a numpy array to a ROOT dataframe with awkward
    '''
    log.info(f'This is try: {itry}')
    d_data = {
            'x' : numpy.array([1, 2, 3]),
            'y' : numpy.array([4, 5, 6]),
            }

    rdf = RDF.FromNumpy(d_data)
    rdf = rdf.Define('z', 'ROOT::RVec<int>({1, 2, 3})')
    rdf = rdf.Define('w', 'true')

    arr_val = numpy.array([10, 20, 30])

    rdf = ut.add_column(rdf, arr_val, 'values')

    rdf.Display().Print()
# -------------------------------------------------
@pytest.mark.parametrize('itry', [1, 2])
def test_add_column_with_numba(itry : int):
    '''
    Will test adding a numpy array to a ROOT dataframe with numba
    '''
    log.info(f'This is try: {itry}')
    d_data = {
            'x' : numpy.array([1, 2, 3]),
            'y' : numpy.array([4, 5, 6]),
            }

    rdf = RDF.FromNumpy(d_data)
    rdf = rdf.Define('z', 'ROOT::RVec<int>({1, 2, 3})')
    rdf = rdf.Define('w', 'true')

    arr_val = numpy.array([10, 20, 30])

    rdf = ut.add_column_with_numba(rdf, arr_val, 'values', identifier=str(itry))

    rdf.Display().Print()
# -------------------------------------------------
def test_misalignment():
    '''
    Will test with inputs where columns have different sizes
    '''
    d_data = {
            'x' : numpy.array([1, 2, 3]),
            'y' : numpy.array([4, 5, 6]),
            }

    rdf     = RDF.FromNumpy(d_data)
    arr_val = numpy.array([10, 20])

    with pytest.raises(ValueError):
        rdf = ut.add_column(rdf, arr_val, 'z')

    rdf.Display().Print()
# -------------------------------------------------
def test_rdf_report_to_df():
    '''
    Will test with inputs where columns have different sizes
    '''
    d_data = {
        'x' : numpy.random.uniform(0,1,1000),
        'y' : numpy.random.uniform(0,1,1000)}

    rdf  = RDF.FromNumpy(d_data)
    rep  = rdf.Report()
    with pytest.raises(ValueError):
        df = ut.rdf_report_to_df(rep)

    rdf  = rdf.Filter('x > 0.2', 'x')
    rdf  = rdf.Filter('y > 0.2', 'y')

    rep  = rdf.Report()
    df   = ut.rdf_report_to_df(rep)

    print(df)
# -------------------------------------------------
@pytest.mark.parametrize('val', [-1, 0, 100_000, 1000_000, 2000_000])
def test_rdf_random(val : int):
    '''
    This function will check that one can
    get a random subset of entries from a ROOT dataframe
    '''
    tot = 1000_000
    rdf = RDataFrame(tot)
    rdf = rdf.Define('a', '1')

    rdf = ut.random_filter(rdf, entries=val)

    res = rdf.Count().GetValue()

    if val <= 0 or val >= tot:
        tar = tot
    else:
        tar = val

    assert math.isclose(tar, res, rel_tol=0.01)
# -------------------------------------------------
def test_rdf_to_df():
    '''
    Will test method making pandas dataframe from ROOT dataframe
    '''
    d_data = {
        'x' : numpy.random.uniform(0,1,1000),
        'y' : numpy.random.uniform(0,1,1000)}

    rdf  = RDF.FromNumpy(d_data)
    df   = ut.rdf_to_df(rdf=rdf, columns=['x', 'y'])

    print(df)
# -------------------------------------------------
