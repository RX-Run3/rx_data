'''
This module contains functions needed by tests
'''
import yaml

from rx_common    import Component, Cuts
from rx_common    import Trigger
from rx_common    import Qsq 
from rx_selection import selection as sel
from rx_data      import RDFGetter
from ROOT         import RDF # type: ignore
from dmu          import LogStore

log=LogStore.add_logger('rx_data:testing')

l_trigger_ee  = [
    Trigger.rk_ee_os   ,
    Trigger.rk_ee_misid,
    Trigger.rkst_ee_os ,
    Trigger.rkst_ee_misid]

l_prefix_kind = [
    ('Hlt2RD_BuToKpEE'     , 'mc_ee'),
    ('Hlt2RD_BuToKpEE'     , 'dt_ss'),
    ('Hlt2RD_BuToKpEE'     , 'dt_ee'),
    ('Hlt2RD_BuToKpEE'     , 'dt_mi'),
    # -----------
    ('Hlt2RD_B0ToKpPimEE'  , 'mc_ee'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ss'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ee'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_mi'),
    # -----------
    ('Hlt2RD_BuToKpMuMu'   , 'mc_mm'),
    ('Hlt2RD_BuToKpMuMu'   , 'dt_mm'),
    # -----------
    ('Hlt2RD_B0ToKpPimMuMu', 'mc_mm'),
    ('Hlt2RD_B0ToKpPimMuMu', 'dt_mm')]

l_prefix_kind_data = [
    ('Hlt2RD_BuToKpEE'     , 'dt_ss'),
    ('Hlt2RD_BuToKpEE'     , 'dt_ee'),
    ('Hlt2RD_BuToKpEE'     , 'dt_mi'),
    # -----------
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ss'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ee'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_mi'),
    # -----------
    ('Hlt2RD_BuToKpMuMu'   , 'dt_mm'),
    ('Hlt2RD_B0ToKpPimMuMu', 'dt_mm')]

l_prefix_kind_bplus = [
    ('Hlt2RD_BuToKpEE'     , 'mc_ee'),
    ('Hlt2RD_BuToKpEE'     , 'dt_ss'),
    ('Hlt2RD_BuToKpEE'     , 'dt_ee'),
    ('Hlt2RD_BuToKpEE'     , 'dt_mi'),
    # -----------
    ('Hlt2RD_BuToKpMuMu'   , 'mc_mm'),
    ('Hlt2RD_BuToKpMuMu'   , 'dt_mm')]

l_prefix_kind_bzero = [
    ('Hlt2RD_B0ToKpPimEE'  , 'mc_ee'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ss'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_ee'),
    ('Hlt2RD_B0ToKpPimEE'  , 'dt_mi'),
    # -----------
    ('Hlt2RD_B0ToKpPimMuMu', 'mc_mm'),
    ('Hlt2RD_B0ToKpPimMuMu', 'dt_mm')]
# ----------------------------------
def get_rdf(kind : str, prefix : str) -> RDF.RNode:
    '''
    Parameters
    ------------------
    kind  : Represents type of sample, dt_ss, dt_ee, dt_mi, dt_mm, mc_ee, mc_mm
    prefix: Trigger name substring, before _MVA

    Returns
    ------------------
    ROOT dataframe with actual data or MC
    '''
    if   kind == 'dt_ss':
        sample = Component.data_24 
    elif kind == 'dt_ee':
        sample = Component.data_24 
    elif kind == 'dt_mi':
        sample = Component.data_24 
    elif kind == 'dt_mm':
        sample = Component.data_24 
    elif kind == 'mc_ee':
        sample = Component.bdkstkpiee
    elif kind == 'mc_mm':
        sample = Component.bdkstkpimm 
    else:
        raise ValueError(f'Invalid dataset of kind/prefix: {kind}/{prefix}')

    trigger = get_trigger(kind = kind, prefix = prefix)

    with RDFGetter.only_friends(s_friend = set()):
        rdf = rdf_from_sample(sample=sample, trigger=trigger)

    return rdf
# ----------------------------------
def rdf_from_sample(
    sample          : Component, 
    trigger         : Trigger,
    nentries        : int  = 10_000,
    apply_selection : bool =  False) -> RDF.RNode:
    '''
    Parameters
    --------------
    nentries       : Filter this number of entries
    apply_selection: If true will apply full selection

    Returns
    --------------
    ROOT dataframe
    '''
    with RDFGetter.max_entries(value = nentries):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    if not apply_selection:
        return rdf

    rdf, d_cut = _apply_selection(rdf=rdf, trigger=trigger, sample=sample)

    nentries = rdf.Count().GetValue()
    if nentries == 0:
        rep = rdf.Report()
        rep.Print()

        print(yaml.dump(d_cut))

        raise ValueError(f'No entry passed for {sample}/{trigger}')

    return rdf
# ----------------------------------
def _apply_selection(
    rdf     : RDF.RNode, 
    trigger : Trigger, 
    sample  : Component) -> tuple[RDF.RNode, dict[Cuts,str]]:
    d_sel               = sel.selection(trigger=trigger, q2bin=Qsq.jpsi, process=sample)
    d_sel[Cuts.pid_l]      = '(1)'
    d_sel[Cuts.jpsi_misid] = '(1)'
    d_sel[Cuts.cascade]    = '(1)'
    d_sel[Cuts.hop]        = '(1)'

    for cut_name, cut_expr in d_sel.items():
        log.debug(f'{cut_name:<20}{cut_expr}')
        rdf = rdf.Filter(cut_expr, cut_name)

    rep   = rdf.Report()
    rep.Print()

    return rdf, d_sel
# ----------------------
def get_trigger(kind : str, prefix : str) -> Trigger:
    '''
    Parameters
    -------------
    kind: Signals sample type
    prefix: Start of the trigger name

    Returns
    -------------
    HLT2 trigger name
    '''
    if kind.endswith('_ss'):
        suffix = '_SameSign_MVA'
    elif kind.endswith('_mi'):
        suffix = '_MVA_misid'
    elif kind.endswith(('_ee', '_mm')):
        suffix = '_MVA'
    else:
        raise ValueError(f'Invalid kind: {kind}')

    return Trigger.from_name(name = f'{prefix}{suffix}')
# ----------------------
