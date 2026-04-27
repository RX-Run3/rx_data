'''
Module needed to test Combinatorial validator class
'''
import numpy

import pytest

from pathlib     import Path
from scipy.stats import truncexpon
from ROOT        import RDF # type: ignore
from fitter      import CmbValidator
from fitter      import CmbInputConfig, CmbValidatorConf, CmbValidationConfig
from fitter      import CmbOutputConfig
from rx_common   import Component, Mass, Qsq, Trigger
from dmu         import LogStore
from dmu.stats   import ZFitPlotterConf
from dmu.generic  import utilities as gut
from dmu.plotting import BandPlotter, BandPlotterConf

log=LogStore.add_logger('fitter:test_cmb_validator')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:cmb_validator', 10)
# ----------------------
def _get_rdf(mass : Mass) -> RDF.RNode:
    '''
    Returns dataframe with fake data
    '''
    size = 100_000
    data : dict[str,numpy.ndarray] = {
        'mva_cmb' : numpy.random.uniform(0, 1, size = size),
        'mva_prc' : numpy.random.uniform(0, 1, size = size),
        mass      : truncexpon.rvs(b=2.5, loc=4500, scale=1000, size=size)
    }

    rdf = RDF.FromNumpy(data)

    return rdf
# ----------------------
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('cutflow', ['cmb_window'])
def test_config(
    tmp_path: Path,
    mass    : Mass,
    cutflow : str):
    '''
    Validate configuration
    '''
    input      = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        trigger = Trigger.rk_ee_ss,
        sample  = Component.data_24,
        cutflow = cutflow,
    )

    output      = CmbOutputConfig(
        dir_path= tmp_path,
        plots   = ZFitPlotterConf.default(),
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/test_config.yaml') 

    return CmbValidatorConf(
        input      = input,
        validation = validation,
        output     = output)
# ----------------------
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('cutflow', ['cmb_window'])
def test_validator(
    tmp_path: Path,
    mass    : Mass,
    cutflow : str):
    '''
    Test actual validation
    '''
    input       = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        trigger = Trigger.rk_ee_ss,
        sample  = Component.data_24,
        cutflow = cutflow,
    )

    output      = CmbOutputConfig(
        dir_path= tmp_path,
        plots   = ZFitPlotterConf.default(),
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/test_config.yaml') 

    cfg = CmbValidatorConf(
        input      = input,
        validation = validation,
        output     = output,
    )

    rdf = _get_rdf(mass = mass)

    obj = CmbValidator(
        rdf = rdf,
        cfg = cfg)
    res = obj.run(label = 'test')
    df  = res.df

    data    = gut.load_data(
        package = 'fitter_data', 
        fpath   = 'combinatorial/test_plots.yaml')
    data['out_dir'] = tmp_path

    cfg_plt = BandPlotterConf(**data)
    cfg_plt = cfg_plt.model_copy(update = {'out_dir' : tmp_path})

    ptr = BandPlotter(df = df, cfg = cfg_plt)
    ptr.plot()
# ----------------------
