'''
Module containing tests for HOPVarAdder
'''
import os
import pytest
import matplotlib.pyplot as plt

from ROOT       import RDF
from pathlib    import Path
from dmu        import LogStore
from rx_common  import Component, Trigger
from rx_data    import HOPCalculator
from rx_data    import MisCalculator
from rx_data    import testing as tst
from rx_data    import RDFGetter

# ----------------------------
class Data:
    '''
    Class used to share attributes
    '''
    nentries= 100_000
    user    = os.environ['USER']
# ----------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before tests
    '''
    LogStore.set_level('rx_data:hop_calculator', 10)

    with RDFGetter.only_friends(s_friend = set()):
        yield
# ----------------------------
def _get_rdf(kind : str, prefix : str) -> RDF.RNode:
    trigger = tst.get_trigger(kind = kind, prefix = prefix)

    rdf = tst.get_rdf(kind=kind, prefix=prefix)
    mcl = MisCalculator(rdf=rdf, trigger=trigger)
    rdf = mcl.get_rdf()

    return rdf
# ----------------------------
def _plot_variables(rdf : RDF.RNode, rdf_hop : RDF.RNode, name : str, tmp_path : Path) -> None:
    out_dir = tmp_path/name
    out_dir.mkdir(parents=True, exist_ok=True)

    d_data = rdf_hop.AsNumpy(['hop_alpha', 'hop_mass'])
    arr_ms = rdf.AsNumpy(['B_M'])['B_M']

    plt.hist(d_data['hop_alpha'], bins=40, range=(0,5))
    plt.savefig(f'{out_dir}/alpha.png')
    plt.close()

    plt.hist(d_data['hop_mass'], bins=40, histtype='step', label='HOP'     , range=(3_000, 8_000))
    plt.hist(            arr_ms, bins=40, histtype='step', label='Original', range=(3_000, 8_000))
    plt.legend()
    plt.title(name)
    plt.savefig(f'{out_dir}/mass.png')
    plt.close()
# ----------------------------
def _compare_sig_bkg(rdf_sig : RDF.RNode, rdf_bkg : RDF.RNode, name : str, tmp_path : Path) -> None:
    out_dir = f'{tmp_path}/{name}'
    os.makedirs(out_dir, exist_ok=True)

    arr_sig = rdf_sig.AsNumpy(['hop_mass'])['hop_mass']
    arr_bkg = rdf_bkg.AsNumpy(['hop_mass'])['hop_mass']

    plt.hist(arr_sig, range=(3000, 6000), bins=50, histtype='step', density=True, label='Signal')
    plt.hist(arr_bkg, range=(3000, 6000), bins=50, histtype='step', density=True, label='Background')

    plt.legend()
    plt.savefig(f'{out_dir}/mass.png')
    plt.close()
# ----------------------------
def _get_hop(rdf : RDF.RNode, trigger : Trigger) -> tuple[RDF.RNode, RDF.RNode]:
    obj     = HOPCalculator(rdf=rdf, trigger=trigger)
    rdf_hop = obj.get_rdf(preffix='hop')

    return rdf_hop, rdf
# ----------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind)
def test_mc(prefix : str, kind : str, tmp_path : Path):
    '''
    Test on MC
    '''
    trigger          = tst.get_trigger(kind = kind, prefix = prefix)
    rdf              = _get_rdf(kind=kind, prefix=prefix)
    rdf_hop, rdf_org = _get_hop(rdf=rdf, trigger=trigger)

    _plot_variables(rdf=rdf_org, rdf_hop=rdf_hop, name=f'mc_{prefix}_{kind}', tmp_path = tmp_path)
# ----------------------------
def test_compare_bukee(tmp_path : Path):
    '''
    Compare signal with background for Bu -> K ee decays
    '''
    trigger = Trigger.rk_ee_os
    sig_sam = Component.bpkpee  
    bkg_sam = Component.bdkstkpiee 
    rdf_sig = tst.rdf_from_sample(sample=sig_sam, trigger=trigger)
    rdf_bkg = tst.rdf_from_sample(sample=bkg_sam, trigger=trigger)

    rdf_sig, _ = _get_hop(rdf = rdf_sig, trigger=trigger)
    rdf_bkg, _ = _get_hop(rdf = rdf_bkg, trigger=trigger)

    _compare_sig_bkg(rdf_sig, rdf_bkg, 'compare_bukee', tmp_path = tmp_path)
# ----------------------------
def test_compare_bdkstee(tmp_path : Path):
    '''
    Compare signal with background for Bd -> Kpi ee decays
    '''
    trigger = Trigger.rkst_ee_os
    sig_sam = Component.bdkstkpiee 
    bkg_sam = Component.bpk1kpipiee 
    rdf_sig = tst.rdf_from_sample(sample=sig_sam, trigger=trigger)
    rdf_bkg = tst.rdf_from_sample(sample=bkg_sam, trigger=trigger)

    rdf_sig, _ = _get_hop(rdf = rdf_sig, trigger=trigger)
    rdf_bkg, _ = _get_hop(rdf = rdf_bkg, trigger=trigger)

    _compare_sig_bkg(rdf_sig, rdf_bkg, 'compare_bdkstee', tmp_path = tmp_path)
# ----------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_extra_branches(trigger : Trigger):
    '''
    Testing adding extra branches to RDF
    '''
    sample  = Component.bdkstkpiee
    rdf     = tst.rdf_from_sample(sample = sample, trigger=trigger)

    obj     = HOPCalculator(rdf=rdf, trigger=trigger)
    rdf_hop = obj.get_rdf(preffix='hop')
    l_col   = [ name.c_str() for name in rdf_hop.GetColumnNames() ]

    assert 'EVENTNUMBER' in l_col
    assert 'RUNNUMBER'   in l_col
# ----------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind_data)
def test_data(kind : str, prefix : str, tmp_path : Path):
    '''
    Test with data
    '''
    trigger = tst.get_trigger(kind = kind, prefix = prefix)
    rdf     = _get_rdf(kind=kind, prefix=prefix)

    rdf_hop, rdf_org = _get_hop(rdf=rdf, trigger=trigger)

    _plot_variables(rdf=rdf_org, rdf_hop=rdf_hop, name=f'data_{kind}_{trigger}', tmp_path = tmp_path)
# ----------------------------
