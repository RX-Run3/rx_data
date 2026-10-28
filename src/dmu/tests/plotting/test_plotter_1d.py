'''
Unit test for plotter class in dmu.plotting
'''
import pytest
import matplotlib.pyplot as plt
import yaml
import numpy
import mplhep

from importlib.resources     import files
from pathlib                 import Path
from typing                  import cast, overload, Literal
from ROOT                    import RDF
from omegaconf               import DictConfig, OmegaConf
from dmu.plotting.plotter_1d import Plotter1D as Plotter
from dmu.logging.log_store   import LogStore

log = LogStore.add_logger('dmu:plotting:test_plotter_1d')
#---------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will be ran before any test
    '''
    plt.style.use(mplhep.style.LHCb2)

    LogStore.set_level('dmu:plotting:Plotter'  , 10)
    LogStore.set_level('dmu:plotting:Plotter1D', 10)
#---------------------------------------
def _get_rdf(
    kind     : str, 
    test     : str      = 'standard', 
    nentries : int|None = None) -> RDF.RNode:
    '''
    kind (str): "class A" or "class B", equivalent to data or mc, but general
    test (str): Identifies specific test
    nentries  : Number of entries to use in dataframe
    '''
    if nentries is not None:
        pass
    elif test == 'high_stat':
        nentries = 1_000_000
    elif test == 'standard':
        nentries =   100_000
    else:
        raise ValueError(f'Invalid kind of test: {test}')

    d_data = {}
    if   kind == 'errors':
        d_data['x_err'] = numpy.random.chisquare(df=4, size=nentries)
        d_data['x_unc'] = numpy.random.poisson(lam=50, size=nentries)
    elif kind == 'pull':
        d_data['x_pul'] = numpy.random.normal(0, 1, size=nentries)
        d_data['y_pul'] = numpy.random.normal(0, 1, size=nentries)
    elif kind == 'class A':
        d_data['x'] = numpy.random.normal(0, 1, size=nentries)
        d_data['y'] = numpy.random.normal(0, 2, size=nentries)
    elif kind == 'class B':
        d_data['x'] = numpy.random.normal(1, 1, size=nentries)
        d_data['y'] = numpy.random.normal(1, 2, size=nentries)
    elif kind == 'class C':
        d_data['x'] = numpy.random.uniform(-10, +10, size=nentries)
        d_data['y'] = numpy.random.uniform(-10, +10, size=nentries)
    else:
        raise ValueError(f'Invalid class: {kind}')

    d_data['weights'] = numpy.random.normal(0.5, 0.1, size=nentries)
    rdf = RDF.FromNumpy(d_data)

    return rdf
#---------------------------------------
@overload
def _load_config(test : str, out_dir : Path, as_dict : Literal[True]) -> dict:...
@overload
def _load_config(test : str, out_dir : Path, as_dict : Literal[False]) -> DictConfig:...
def _load_config(test : str, out_dir : Path, as_dict : bool = True) -> dict|DictConfig:
    '''
    test (str): Identifies specific test
    '''

    cfg_path = files('dmu_data').joinpath(f'plotting/tests/{test}.yaml')
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf-8') as ifile:
        cfg = yaml.safe_load(ifile)

    cfg['saving']['plt_dir'] = out_dir 

    if as_dict:
        return cfg

    ocfg = OmegaConf.create(cfg)
    ocfg = cast(DictConfig, ocfg)

    return ocfg
#---------------------------------------
def test_simple(tmp_path : Path):
    '''
    Minimal test
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='simple',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_omega_conf(tmp_path : Path):
    '''
    Testing config passed through DictConfig
    '''
    d_rdf   =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }
    cfg_dat = _load_config(test='simple',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_line(tmp_path : Path):
    '''
    Tests config that places lines on figure
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='line',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_styling(tmp_path : Path):
    '''
    Change style of histogram plots
    '''
    d_rdf   =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }
    cfg_dat = _load_config(test='styling',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_high_stat(tmp_path : Path):
    '''
    Test for large datasets
    '''
    d_rdf =  { kind : _get_rdf(kind=kind, test='high_stat') for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='high_stat',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_no_bounds(tmp_path : Path):
    '''
    Test for case where plot bounds are not explicitly passed
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='no_bounds',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_fig_size(tmp_path : Path):
    '''
    Test for fig size setting
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='fig_size',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_title(tmp_path : Path):
    '''
    Test for title
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='title',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_weights(tmp_path : Path):
    '''
    Tests plotting with weights
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='weights',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_name(tmp_path : Path):
    '''
    Testing the use of the name key, to name PNG files
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='name',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_normalized(tmp_path : Path):
    '''
    Will test the plot of normalized histograms
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='normalized',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_legend(tmp_path : Path):
    '''
    Tests legend options
    '''
    d_rdf =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }

    cfg_dat = _load_config(test='legend',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_plugin_fwhm(tmp_path : Path):
    '''
    Will test fwhm plugin
    '''
    log.info('')
    d_rdf   =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B'] }
    cfg_dat = _load_config(test='plug_fwhm',  as_dict=False, out_dir = tmp_path)
    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_plugin_stats(tmp_path : Path):
    '''
    Will test stats plugin
    '''
    log.info('')
    d_rdf   =  { kind : _get_rdf(kind=kind) for kind in ['class A', 'class B', 'class C'] }
    cfg_dat = _load_config(test='plug_stats',  as_dict=False, out_dir = tmp_path)
    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_pull_plugin(tmp_path : Path):
    '''
    Test plotting of pull distributions
    '''
    d_rdf   =  { kind : _get_rdf(kind=kind, ) for kind in ['pull'] }
    cfg_dat = _load_config(test='pulls',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
def test_errors_plugin(tmp_path : Path):
    '''
    Test plotting of pull distributions
    '''
    d_rdf   =  { kind : _get_rdf(kind=kind, ) for kind in ['errors'] }
    cfg_dat = _load_config(test='errors',  as_dict=False, out_dir = tmp_path)

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg_dat)
    ptr.run()
#---------------------------------------
