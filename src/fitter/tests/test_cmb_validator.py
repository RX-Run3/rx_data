'''
Module needed to test Combinatorial validator class
'''
import numpy

import pytest
import pandas as pnd

from pathlib      import Path
from scipy.stats  import truncexpon
from ROOT         import RDF
from fitter       import CmbValidator
from fitter       import CmbInputConfig, CmbValidatorConf, CmbValidationConfig
from fitter       import CmbOutputConfig
from rx_common    import Component, Mass, Qsq, Trigger
from dmu          import LogStore
from dmu.stats    import Model, zfit
from dmu.stats    import ModelFactory, ZFitPlotterConf
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
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('cutflow', ['cmb_window'])
def test_config(
    tmp_path: Path,
    mass    : Mass,
    cutflow : str):
    '''
    Validate configuration
    '''
    input_cfg   = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        trigger = Trigger.rk_ee_ss,
        samples = [Component.data_24, Component.bpkpee],
        cutflow = cutflow,
    )

    output_cfg  = CmbOutputConfig(
        dir_path= tmp_path,
        plots   = ZFitPlotterConf.default(),
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/test_parametric.yaml')

    return CmbValidatorConf(
        input      = input_cfg,
        validation = validation,
        output     = output_cfg)
# ----------------------
def _get_mass(
    comp : Component,
    size : int) -> numpy.ndarray:
    '''
    Returns numpy array with masses
    '''
    fac = ModelFactory(
        obs      = zfit.Space('mass', limits = (4500, 6000)),
        l_shared = [],
        l_float  = [],
        l_pdf    = [Model.fermi_dirac],
        preffix  = '')

    pdf     = fac.get_pdf()
    sampler = pdf.create_sampler(size)
    arr_sig = sampler.to_numpy().flatten()

    if comp != Component.data_24:
        return arr_sig

    arr_bkg = truncexpon.rvs(b=2.5, loc=4500, scale=1000, size=size)

    arr_dat = numpy.concatenate([arr_sig, arr_bkg])
    numpy.random.shuffle(arr_dat)

    return arr_dat[:size]
# ----------------------
def _get_rdf(
    mass : Mass,
    comp : Component) -> RDF.RNode:
    '''
    Parameters
    --------------
    mass : Observable that will be fitted in validation
    comp : Fitting component

    Returns
    --------------
    DataFrame with: mva_cmb, mva_prc, mass
    '''

    size = 100_000
    data : dict[str,numpy.ndarray] = {
        'mva_cmb' : numpy.random.uniform(0, 1, size = size),
        'mva_prc' : numpy.random.uniform(0, 1, size = size),
        mass      : _get_mass(comp = comp, size = size),
    }

    rdf = RDF.FromNumpy(data)

    return rdf
# ----------------------
def _get_df(
    cfg : CmbValidatorConf,
    mass: Mass) -> pnd.DataFrame:

    rdfs : dict[Component,RDF.RNode] = {}
    for comp in [Component.data_24, Component.bpkpee]:
        rdfs[comp] = _get_rdf(
            mass   = mass,
            comp   = comp)

    obj = CmbValidator(
        rdfs = rdfs,
        cfg  = cfg)
    res = obj.run(label = 'test')
    df  = res.df

    return df
# ----------------------
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('cutflow', ['cmb_window'])
def test_validation(
    tmp_path: Path,
    mass    : Mass,
    cutflow : str):
    '''
    Test actual validation
    '''
    cfg_input   = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        trigger = Trigger.rk_ee_ss,
        samples = [Component.data_24, Component.bpkpee],
        cutflow = cutflow,
    )

    output      = CmbOutputConfig(
        dir_path= tmp_path,
        plots   = ZFitPlotterConf.default(),
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/test_parametric.yaml')

    cfg = CmbValidatorConf(
        input      = cfg_input,
        validation = validation,
        output     = output,
    )

    l_df : list[pnd.DataFrame] = []
    for cat in ['c1', 'c2']:
        df             = _get_df(cfg = cfg, mass = mass)
        df['Category'] = cat
        l_df.append(df)

    df   = pnd.concat(l_df)
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = 'combinatorial/test_plots.yaml')
    data['out_dir'] = tmp_path

    cfg_plt = BandPlotterConf(**data)
    cfg_plt = cfg_plt.model_copy(update = {'out_dir' : tmp_path})

    ptr = BandPlotter(df = df, cfg = cfg_plt)
    ptr.plot()
# ----------------------
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('cutflow', ['cmb_window'])
def test_kde_fit(
    tmp_path: Path,
    mass    : Mass,
    cutflow : str):
    '''
    Test fitting extra component with kde
    '''
    cfg_input   = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        trigger = Trigger.rk_ee_ss,
        samples = [Component.data_24, Component.bpkpee],
        cutflow = cutflow,
    )

    output      = CmbOutputConfig(
        dir_path= tmp_path,
        plots   = ZFitPlotterConf.default(),
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/test_kde.yaml')

    cfg = CmbValidatorConf(
        input      = cfg_input,
        validation = validation,
        output     = output,
    )

    l_df : list[pnd.DataFrame] = []
    for cat in ['c1', 'c2']:
        df             = _get_df(cfg = cfg, mass = mass)
        df['Category'] = cat
        l_df.append(df)

    df   = pnd.concat(l_df)
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = 'combinatorial/test_plots.yaml')
    data['out_dir'] = tmp_path

    cfg_plt = BandPlotterConf(**data)
    cfg_plt = cfg_plt.model_copy(update = {'out_dir' : tmp_path})

    ptr = BandPlotter(df = df, cfg = cfg_plt)
    ptr.plot()
# ----------------------
