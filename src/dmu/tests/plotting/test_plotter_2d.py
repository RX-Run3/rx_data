'''
Module containing tests for 2D plotter class
'''
from importlib.resources      import files

import yaml
import numpy
import mplhep
import pytest
import matplotlib.pyplot as plt

from ROOT                     import RDF
from dmu.logging.log_store    import LogStore
from dmu.plotting.plotter_2d  import Plotter2D as Plotter

#---------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    '''
    This needs to be ran before any test
    '''
    plt.style.use(mplhep.style.LHCb2)

    LogStore.set_level('dmu:plotting:Plotter', 10)
#---------------------------------------
def _get_rdf(kind : str, test : str, nentries : int = 10_000):
    '''
    kind (str): "class A" or "class B", equivalent to data or mc, but general
    test (str): Identifies specific test
    '''

    if test == 'high_stat':
        nentries = 1_000_000

    d_data = {}
    if   kind == 'class A':
        d_data['x'] = numpy.random.normal(0, 1, size=nentries)
        d_data['y'] = numpy.random.normal(0, 2, size=nentries)
    elif kind == 'class B':
        d_data['x'] = numpy.random.normal(1, 1, size=nentries)
        d_data['y'] = numpy.random.normal(1, 2, size=nentries)
    else:
        raise ValueError(f'Invalid class: {kind}')

    d_data['weights'] = numpy.random.normal(0.5, 0.1, size=nentries)
    rdf = RDF.FromNumpy(d_data)

    return rdf
#---------------------------------------
def _load_config(test : str):
    '''
    test (str): Identifies specific test
    '''

    cfg_path = files('dmu_data').joinpath(f'plotting/tests/{test}.yaml')
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf-8') as ifile:
        cfg = yaml.safe_load(ifile)

    return cfg
#---------------------------------------
def test_simple():
    '''
    Tests for 2D plots
    '''
    name    = '2d'
    rdf     = _get_rdf(kind='class A', test='weights')
    cfg_dat = _load_config(test=name)
    out_path= cfg_dat['saving']['plt_dir']
    cfg_dat['saving']['plt_dir'] = f'{out_path}/simple'

    ptr=Plotter(rdf=rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_empty_log():
    '''
    Tests plotting an empty dataset with log scale for z axis
    '''
    name    = '2d'
    rdf     = _get_rdf(kind='class A', test='weights', nentries = 10)
    rdf     = rdf.Filter('x!=x')

    cfg_dat = _load_config(test=name)
    out_path= cfg_dat['saving']['plt_dir']
    cfg_dat['saving']['plt_dir'] = f'{out_path}/empty_log'

    ptr=Plotter(rdf=rdf, cfg=cfg_dat)
    ptr.run()
