'''
Module used to test bias corrections
'''
import os
import copy
import yaml
import numpy
import mplhep
import pytest
import matplotlib.pyplot as plt

from typing              import Final
from pathlib             import Path
from importlib.resources import files
from omegaconf           import OmegaConf
from ROOT                import RDF
from dmu                 import LogStore
from dmu.plotting        import Plotter1D as Plotter
from rx_data             import utilities as ut
from rx_data             import RDFGetter
from rx_data             import MassBiasCorrector
from rx_common           import Component, Trigger

log=LogStore.add_logger('rx_data:test_mass_bias_corrector')

_SAMPLES_MM = [
    (Component.bpkpjpsimm    , Trigger.rk_mm_os  ),
    (Component.bdkstkpijpsimm, Trigger.rkst_mm_os),
    #----------------
    (Component.data_24_mu_c2 , Trigger.rk_mm_os  ),
    (Component.data_24_mu_c2 , Trigger.rkst_mm_os),
]

_SAMPLES_EE = [
    (Component.bpkpjpsiee    , Trigger.rk_ee_os  ),
    (Component.bdkstkpijpsiee, Trigger.rkst_ee_os),
    #----------------
    (Component.data_24_mu_c2 , Trigger.rk_ee_os  ),
    (Component.data_24_mu_c2 , Trigger.rkst_ee_os),
]

_SAMPLES_DATA = [
    (Component.data_24_mu_c2, Trigger.rk_mm_os  ),
    (Component.data_24_mu_c2, Trigger.rkst_mm_os),
    #----------------
    (Component.data_24_mu_c2, Trigger.rk_ee_os  ),
    (Component.data_24_mu_c2, Trigger.rkst_ee_os),
    #----------------
    (Component.data_24_mu_c3, Trigger.rk_mm_os  ),
    (Component.data_24_mu_c3, Trigger.rkst_mm_os),
    #----------------
    (Component.data_24_mu_c3, Trigger.rk_ee_os  ),
    (Component.data_24_mu_c3, Trigger.rkst_ee_os),
]

_SAMPLES = _SAMPLES_MM + _SAMPLES_EE
_NCOLS : Final[int] = 18
_PHOTON_VETO_VERSIONS : Final[list[str]] = ['v0', 'v1', 'v2']
#-----------------------------------------
class Data:
    '''
    Data class
    '''
    user       = os.environ['USER']
    nthreads   = 13
    nentries   = -1
#-----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before tests
    '''
    LogStore.set_level('rx_data:mass_bias_corrector'     , 10)
    LogStore.set_level('rx_data:electron_bias_corrector' , 20)
    LogStore.set_level('rx_data:test_mass_bias_corrector', 10)
    LogStore.set_level('rx_data:rdf_getter'              , 10)

    plt.style.use(mplhep.style.LHCb2)
#-----------------------------------------
def _load_conf() -> dict:
    cfg_path = files('rx_data_data').joinpath('tests/mass_bias_corrector/mass_overlay.yaml')
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf-8') as ifile:
        cfg = yaml.safe_load(ifile)

    return cfg
# ----------------------
def _check_corrected(
    rdf_unc : RDF.RNode,
    rdf_cor : RDF.RNode,
    trigger : str,
    name    : str) -> int:
    '''
    Parameters
    -------------
    trigger : Needed to know if sample should be corrected, muon trigger should not
    name    : Variable to be checked
    rdf     : DataFrame after correction

    Returns
    -------------
    Number of candidates that were corrected
    '''
    arr_val_unc = rdf_unc.AsNumpy([name])[name]
    arr_val_cor = rdf_cor.AsNumpy([name])[name]

    # If any mass is NaN, it will be dropped from comparison
    # NaN means a track kinematic or brem energy is NaN
    arr_ind_pos = numpy.where(arr_val_cor > 0)
    arr_val_unc = arr_val_unc[arr_ind_pos]
    arr_val_cor = arr_val_cor[arr_ind_pos]

    if 'MuMu' in trigger:
        assert numpy.isclose(arr_val_unc, arr_val_cor, atol=1).all()
        return 0

    arr_shift   = numpy.abs(arr_val_cor - arr_val_unc)
    arr_shift   = arr_shift[arr_shift > 1]
    log.verbose(20 * '-')
    log.verbose(f'Shift in {name} mass:')
    log.verbose(20 * '-')
    for shift in arr_shift:
        log.verbose(shift)

    # A mass will be considered unchaged if the difference is less than 1 MeV
    arr_flag    = numpy.isclose(arr_val_unc, arr_val_cor, atol=1).astype(int)
    total       = len(arr_flag)
    uncorrected = numpy.sum(arr_flag)
    corrected   = total - uncorrected

    # Somewhere between 20% and 70% of candidates should change with brem correction
    assert corrected / total < 1

    return corrected
# ----------------------
def _clean_rdf(rdf : RDF.RNode) -> RDF.RNode:
    rdf = rdf.Filter('Jpsi_M > 0', 'pos_jmass')
    rdf = rdf.Filter('B_M    > 0', 'pos_bmass')

    rep = rdf.Report()
    rep.Print()

    return rdf
#-----------------------------------------
def _compare_masses(
    d_rdf      : dict[str, RDF.RNode],
    test_name  : str,
    correction : str,
    out_dir    : Path,
    skip_jpsi  : bool=False) -> None:
    '''
    d_rdf     : Dictionary with corrected and original dataframes
    test_name : Used for output path
    correction: Correction name, used for title
    skip_jpsi : If false, will plot Jpsi_M distributin
    '''
    d_rdf = { name : _clean_rdf(rdf) for name, rdf in d_rdf.items() }

    dat = _load_conf()
    dat = copy.deepcopy(dat)
    cfg = OmegaConf.create(dat)

    plt_dir = f'{out_dir}/{test_name}'

    cfg['saving'] = {'plt_dir' : plt_dir}

    cfg['plots']['B_M'   ]['title'] = correction

    if not skip_jpsi:
        cfg['plots']['Jpsi_M']['title'] = correction
    else:
        del cfg['plots']['Jpsi_M']

    ptr=Plotter(d_rdf=d_rdf, cfg=cfg)
    ptr.run()
#-----------------------------------------
def _check_input_columns(rdf : RDF.RNode) -> None:
    l_colname = [ name.c_str() for name in rdf.GetColumnNames() ]

    l_track_brem = [ name for name in l_colname if name.endswith('BREMTRACKBASEDENERGY') ]

    if len(l_track_brem) == 0:
        for colname in l_colname:
            log.warning(colname)
        raise ValueError('No BREMTRACKBASEDENERGY found')

    log.info(f'Found: {l_track_brem}')
#-----------------------------------------
def _check_output_columns(rdf : RDF.RNode) -> None:
    l_colname = [ name.c_str() for name in rdf.GetColumnNames() ]
    ncol = len(l_colname)
    if ncol != _NCOLS:
        for colname in l_colname:
            log.info(f'   {colname}')

        raise ValueError(f'Expected 18 columns, got {ncol}')

    for colname in l_colname:
        log.debug(f'   {colname}')
#-----------------------------------------
def _get_rdf(
    trigger  : Trigger,
    sample   : Component) -> RDF.RNode:
    '''
    Return ROOT dataframe needed for test

    nbrem : E.g. 0, 1, 2
    '''
    with RDFGetter.only_friends(s_friend=set()):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    _check_input_columns(rdf)

    nentries = rdf.Count().GetValue()
    if nentries == 0:
        rep = rdf.Report()
        rep.Print()
        raise ValueError('Empty dataframe found')
    else:
        log.info(f'Found {nentries} entries')

    return rdf
# ----------------------
def _check_size(rdf_org : RDF.RNode, rdf_cor : RDF.RNode) -> None:
    '''
    Parameters
    -------------
    rdf_org: Input dataframe, needed to be corrected
    rdf_cor: Dataframe with corrected data
    '''
    in_size = rdf_org.Count().GetValue()
    ot_size = rdf_cor.Count().GetValue()

    assert in_size == ot_size

    log.info(f'Sizes agree at: {in_size}')
#-----------------------------------------
@pytest.mark.parametrize('sample, trigger'    , _SAMPLES_EE)
@pytest.mark.parametrize('photon_veto_version', _PHOTON_VETO_VERSIONS)
def test_simple(
    photon_veto_version : str,
    sample              : Component,
    trigger             : Trigger,
    tmp_path            : Path):
    '''
    Simplest test
    '''
    kind    = 'brem_track_2'
    with RDFGetter.max_entries(value = 1000):
        rdf_org = _get_rdf(sample = sample, trigger = trigger)

    df_org  = ut.df_from_rdf(rdf=rdf_org, drop_nans=False)
    is_mc   = ut.rdf_is_mc(rdf=rdf_org)

    cor_1   = MassBiasCorrector(
        photon_veto_version= photon_veto_version,
        skip_correction    = True,
        df                 = df_org,
        is_mc              = is_mc,
        trigger            = trigger,
        ecorr_kind         = kind)

    cor_2   = MassBiasCorrector(
        photon_veto_version= photon_veto_version,
        skip_correction    = False,
        df                 = df_org,
        is_mc              = is_mc,
        trigger            = trigger,
        ecorr_kind         = kind)

    df_unc  = cor_1.get_df()
    rdf_unc = RDF.FromPandas(df_unc)

    df_cor  = cor_2.get_df()
    rdf_cor = RDF.FromPandas(df_cor)

    _check_size(rdf_org=rdf_org, rdf_cor=rdf_cor)
    _check_output_columns(rdf_cor)
    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name=   'B_M')
    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name='Jpsi_M')

    d_rdf   = {'Original' : rdf_org, 'Corrected' : rdf_cor}
    _compare_masses(d_rdf, f'simple/{trigger}', kind, out_dir = tmp_path)
#-----------------------------------------
@pytest.mark.parametrize('sample, trigger'    , _SAMPLES_DATA)
@pytest.mark.parametrize('photon_veto_version', _PHOTON_VETO_VERSIONS)
def test_medium_input(
    photon_veto_version : str,
    sample              : Component,
    trigger             : Trigger,
    tmp_path            : Path):
    '''
    Medium input
    '''
    kind    = 'brem_track_2'
    with RDFGetter.max_entries(100_000):
        rdf_org = _get_rdf(sample=sample, trigger=trigger)

    df_org  = ut.df_from_rdf(rdf=rdf_org, drop_nans=False)
    is_mc   = ut.rdf_is_mc(rdf=rdf_org)

    cor_1   = MassBiasCorrector(
        photon_veto_version = photon_veto_version,
        skip_correction     = True,
        df                  = df_org,
        is_mc               = is_mc,
        trigger             = trigger,
        ecorr_kind          = kind)

    cor_2   = MassBiasCorrector(
        photon_veto_version = photon_veto_version,
        skip_correction     = False,
        df                  = df_org,
        is_mc               = is_mc,
        trigger             = trigger,
        ecorr_kind          = kind)

    df_unc  = cor_1.get_df()
    rdf_unc = RDF.FromPandas(df_unc)

    df_cor  = cor_2.get_df()
    rdf_cor = RDF.FromPandas(df_cor)

    _check_size(rdf_org=rdf_org, rdf_cor=rdf_cor)
    _check_output_columns(rdf_cor)
    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name=   'B_M')
    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name='Jpsi_M')

    d_rdf   = {'Original' : rdf_org, 'Uncorrected' : rdf_unc, 'Corrected' : rdf_cor}
    _compare_masses(d_rdf, f'medium_{sample}/{trigger}', kind, out_dir = tmp_path)
#-----------------------------------------
@pytest.mark.parametrize('sample, trigger', _SAMPLES)
def test_suffix(sample : Component, trigger : Trigger):
    '''
    Tests that output dataframe has columns with suffix added
    '''
    kind = 'brem_track_2'
    with RDFGetter.max_entries(value = 1000):
        rdf_org = _get_rdf(sample=sample, trigger=trigger)

    df_org  = ut.df_from_rdf(rdf=rdf_org, drop_nans=False)
    is_mc   = ut.rdf_is_mc(rdf=rdf_org)

    cor     = MassBiasCorrector(
        photon_veto_version = 'v0',
        df                  = df_org,
        trigger             = trigger,
        is_mc               = is_mc,
        ecorr_kind          = kind)

    df_cor = cor.get_df(suffix=kind)
    rdf_cor= RDF.FromPandas(df_cor)

    _check_output_columns(rdf_cor)
#-----------------------------------------
@pytest.mark.parametrize('sample, trigger', _SAMPLES)
@pytest.mark.parametrize('brem_energy_threshold', [100, 200, 300, 400, 600, 800, 1000, 1500, 2000, 4000])
def test_brem_threshold(sample : Component, trigger : Trigger, brem_energy_threshold: float, tmp_path : Path):
    '''
    Vary energy threhold of brem photon needed to be added
    '''
    with RDFGetter.max_entries(value=1000):
        rdf_org = _get_rdf(sample=sample, trigger=trigger)

    df_org  = ut.df_from_rdf(rdf=rdf_org, drop_nans=False)
    is_mc   = ut.rdf_is_mc(rdf=rdf_org)

    cor_1   = MassBiasCorrector(
        photon_veto_version  ='v0',
        df                   =df_org,
        trigger              =trigger,
        is_mc                =is_mc,
        skip_correction      =True,
        brem_energy_threshold=brem_energy_threshold)

    cor_2   = MassBiasCorrector(
        photon_veto_version  ='v0',
        df                   =df_org,
        trigger              =trigger,
        is_mc                =is_mc,
        skip_correction      =False,
        brem_energy_threshold=brem_energy_threshold)

    df_unc = cor_1.get_df()
    rdf_unc= RDF.FromPandas(df_unc)

    df_cor = cor_2.get_df()
    rdf_cor= RDF.FromPandas(df_cor)

    d_rdf  = {'Original' : rdf_org, 'Uncorrected' : rdf_unc, 'Corrected' : rdf_cor}

    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name=   'B_M')
    _check_corrected(rdf_cor=rdf_cor, rdf_unc=rdf_unc, trigger=trigger, name='Jpsi_M')
    _compare_masses(d_rdf, f'{trigger}/energy_{brem_energy_threshold:03}', f'$E_{{\\gamma}}>{brem_energy_threshold}$ MeV', out_dir = tmp_path)
#-----------------------------------------
