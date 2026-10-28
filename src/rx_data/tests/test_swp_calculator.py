'''
Module with tests for swap calculator class
'''
import mplhep
import pytest
import matplotlib.pyplot as plt

from ROOT      import RDF
from pathlib   import Path
from dmu       import LogStore
from rx_common import Project, Component, Trigger
from rx_data   import SWPCalculator
from rx_data   import testing  as tst
from rx_data   import RDFGetter

log = LogStore.add_logger('rx_data:test_swp_calculator')
# ----------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_data:swp_calculator'     , 20)
    LogStore.set_level('rx_data:test_swp_calculator', 10)
    LogStore.set_level('rx_data:rdf_getter'         , 10)

    plt.style.use(mplhep.style.LHCb2)
    
    with RDFGetter.only_friends(s_friend = set()):
        yield
# ----------------------
def _get_hadron_mapping(trigger : Trigger) -> dict[str,int]:
    '''
    Parameters
    -------------
    preffix: Used to distinguish between triggers

    Returns
    -------------
    dictionary specifying how to swap masses
    '''
    if trigger.project == Project.rk:
        return {'H'  : 321}

    if trigger.project == Project.rkst:
        return {'H1' : 321}

    raise ValueError(f'Invalid trigger: {trigger}')
# ----------------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_ss])
@pytest.mark.parametrize('sample' , [Component.data_24])
def test_dzero_misid(
    trigger  : Trigger, 
    sample   : Component, 
    tmp_path : Path):
    '''
    Tests dzero decay contamination
    '''
    with RDFGetter.only_friends(s_friend = set()):
        rdf = tst.rdf_from_sample(
            sample          = sample, 
            trigger         = trigger,
            apply_selection = False)

    rdf      = rdf.Filter('rdfentry_ < 1000')
    ientries = rdf.Count().GetValue()

    d_had = _get_hadron_mapping(trigger=trigger)

    obj = SWPCalculator(rdf, d_lep={'L1' : 211, 'L2' : 211}, d_had=d_had)
    rdf = obj.get_rdf(preffix='dzero_misid', progress_bar=True, use_ss= trigger.is_ss)

    oentries = rdf.Count().GetValue()

    assert ientries == oentries

    _plot(rdf, test='dzero_misid', kind=sample, prefix=trigger, tmp_path = tmp_path)
# ----------------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind)
def test_phi_misid(prefix : str, kind : str, tmp_path : Path):
    '''
    Tests phi decay contamination
    '''
    rdf     = tst.get_rdf(kind=kind, prefix=prefix)
    trigger = tst.get_trigger(kind = kind, prefix = prefix)

    if   trigger.project == Project.rk: 
        obj = SWPCalculator(rdf, d_lep={'L1' : 321, 'L2' : 321}, d_had={'H' : 321})
    elif trigger.project == Project.rkst: 
        obj = SWPCalculator(rdf, d_lep={'H1' : 321}, d_had={'H2' : 321})
    else:
        raise ValueError(f'Invalid prefix: {prefix}')

    rdf = obj.get_rdf(preffix='phi_misid', progress_bar=True, use_ss= 'ss' in kind)

    _plot(rdf, test='phi_misid', kind=kind, prefix=prefix, tmp_path = tmp_path)
# ----------------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind_bplus)
def test_jpsi_misid_bplus(prefix : str, kind : str, tmp_path : Path):
    '''
    Tests jpsi misid contamination when the decay is B -> K ell ell
    '''
    rdf     = tst.get_rdf(kind=kind, prefix=prefix)
    trigger = tst.get_trigger(kind = kind, prefix = prefix)
    name= 'jpsi_misid_bplus'

    if   trigger.is_muon:
        obj = SWPCalculator(rdf, d_lep={'L1' : 13, 'L2' : 13}, d_had={'H' : 13})
    elif trigger.is_electron:
        obj = SWPCalculator(rdf, d_lep={'L1' : 11, 'L2' : 11}, d_had={'H' : 11})
    else:
        raise ValueError(f'Invalid prefix: {prefix}')

    rdf = obj.get_rdf(preffix=name, progress_bar=True, use_ss= 'ss' in kind)

    _plot(rdf, test=name, kind=kind, prefix=prefix, tmp_path = tmp_path)
# ----------------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind_bzero)
def test_jpsi_misid_bzero(prefix : str, kind : str, tmp_path : Path):
    '''
    Tests jpsi misid contamination
    '''
    rdf    = tst.get_rdf(kind=kind, prefix=prefix)
    lep_id = 13 if 'MuMu' in prefix else 11

    name_1= 'jpsi_misid_bzero_kaon'
    obj_1 = SWPCalculator(rdf, d_lep={'L1' : lep_id, 'L2' : lep_id}, d_had={'H1' : lep_id})
    rdf_1 = obj_1.get_rdf(preffix=name_1, progress_bar=True, use_ss= 'ss' in kind)

    name_2= 'jpsi_misid_bzero_pion'
    obj_2 = SWPCalculator(rdf, d_lep={'L1' : lep_id, 'L2' : lep_id}, d_had={'H2' : lep_id})
    rdf_2 = obj_2.get_rdf(preffix=name_2, progress_bar=True, use_ss= 'ss' in kind)

    _plot(rdf_1, test=name_1, kind=kind, tmp_path = tmp_path, prefix=prefix)
    _plot(rdf_2, test=name_2, kind=kind, tmp_path = tmp_path, prefix=prefix)
# ----------------------------------
def _plot(
    rdf     : RDF.RNode, 
    test    : str, 
    kind    : str, 
    tmp_path: Path,
    prefix  : str):
    d_data = rdf.AsNumpy([f'{test}_mass_swp', f'{test}_mass_org'])
    arr_swp= d_data[f'{test}_mass_swp']
    arr_org= d_data[f'{test}_mass_org']

    mass_rng = {
        'jpsi_misid_bplus'      : (2700, 3300),
        'jpsi_misid_bzero_kaon' : (2700, 3300),
        'jpsi_misid_bzero_pion' : (2700, 3300),
        'dzero_misid'           : (1700, 2000),
        'phi_misid'             : ( 980, 1100)}[test]

    plt.hist(arr_org, bins=80, range=mass_rng, alpha=0.5, label='Original', color='gray')
    plt.hist(arr_swp, bins=80, range=mass_rng, histtype='step', label='Swapped', color='blue')
    plt.grid(False)

    if   test.startswith('phi_misid'):
        plt.axvline(x=1020, color='r', label=r'$\phi$', linestyle=':')
    elif test.startswith('jpsi_misid'):
        plt.axvline(x=3100, color='r', label=r'$J/\psi$', linestyle=':')
    elif test.startswith('dzero_misid'):
        plt.axvline(x=1864, color='r', label='$D_0$', linestyle=':')
    else:
        raise ValueError(f'Invalid test name: {test}')

    plt.legend()
    plt.savefig(tmp_path /f'{kind}_{prefix}.png')
    plt.close('all')
# ----------------------------------
