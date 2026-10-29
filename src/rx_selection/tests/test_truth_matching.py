'''
Module needed to test truth matching
'''
import re
import pytest

from ROOT         import RDF
from rx_common    import Component, Trigger
from rx_selection import truth_matching as tm
from rx_data      import RDFGetter
from dmu          import LogStore

# TODO: Add more samples

_EMULATED : list[tuple[Component, Trigger]] = [
    (Component.bskstpsi2ee               , Trigger.rkst_ee_os),
    (Component.bskstpsi2mm               , Trigger.rkst_mm_os),
    # --------
    (Component.bdkstkpijpsimm_kpimm_pikmm, Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee_kpiee_pikee, Trigger.rkst_ee_os),
    # --------
    (Component.bdkstkpijpsimm_kpimm_kmpim, Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee_kpiee_kepie, Trigger.rkst_ee_os),
    # --------
    (Component.bdkstkpijpsimm_kpimm_mpimk, Trigger.rkst_mm_os),
    (Component.bdkstkpijpsiee_kpiee_epiek, Trigger.rkst_ee_os),
    # --------
    (Component.bpkpjpsimm_kmm_mkm        , Trigger.rk_mm_os),
    (Component.bpkpjpsiee_kee_eke        , Trigger.rk_ee_os),
]

_SEMILEPTONIC_SAMPLES_RK = [
    Component.bpdnukpiee,
    Component.bpdnuknuee,
    Component.bpdpiknuee]

_SEMILEPTONIC_SAMPLES_RKST = [
    Component.bdkpienuenu,
    Component.bdkpipienu,
]

_RK_MISIDSAMPLES=[
    Component.bpkkk,
    Component.bpkpipi,
    Component.bpkpik,
    Component.bpkpee,
]

l_sample_kpee = [
    Component.bpjpsixee,
    Component.bdjpsixee,
    Component.bsjpsixee,
    Component.bdkstkpiee,
    Component.bpkpee,
    Component.bsphiee,
    Component.bpkpjpsiee,
    Component.bppijpsiee,
    Component.bpk1kpipiee,
    Component.bpk2kpipiee,
    Component.bpkstkpiee,
    Component.bpkppsi2ee,
]

l_sample_kstee = [
    Component.bpjpsixee,
    Component.bdjpsixee,
    Component.bsjpsixee,
    Component.bdkstkpiee,
    Component.bdkstkpijpsiee,
    Component.bskstjpsiee,
    Component.bsphijpsiee,
    Component.lbpkjpsiee,
    Component.bpkpipiee,
    Component.bpk1kpipiee,
    Component.bpk2kpipiee,
]

l_sample_kpmm = [
    Component.bdkstkpimm,
    Component.bpkpjpsimm,
    Component.bppijpsimm,
    Component.bpkpmm,
]

l_sample_kstmm = [
    Component.bpjpsixmm,
    Component.bdjpsixmm,
    Component.bsjpsixmm,
    Component.bdkstkpimm,
    Component.bdkstkpijpsimm,
    Component.bskstjpsimm,
    Component.bsphijpsimm,
    Component.lbpkjpsimm,
]

l_sample_custom = [
    Component.bpkxkpipiee,
]

log=LogStore.add_logger('rx_selection:test_truth_matching')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:rdf_getter'              , 40)
    LogStore.set_level('rx_selection:truth_matching'     , 10)
    LogStore.set_level('rx_selection:test_truth_matching', 10)
# ----------------------
def _print_values(rdf : RDF.RNode, cut : str, number : int) -> None:
    '''
    This should be ran if zero entries pass the truth matching

    Parameters
    -------------
    rdf   : DataFrame before truth matching
    cut   : Truth matching string
    number: Number of values to print
    '''
    rgx  = r'TMath::Abs\((.*)\)'
    vals = re.findall(rgx, cut)

    if len(vals) != 1:
        raise ValueError(f'Could not find one variable, but: {vals}')

    var = vals[0]

    arr_val = rdf.AsNumpy([var])[var]

    log.info(arr_val[:number])
# ----------------------
def _check_rdf(rdf : RDF.RNode, selection : str) -> None:
    '''
    This should be ran if zero entries pass the truth matching

    Parameters
    -------------
    rdf: DataFrame before truth matching
    cut: Truth matching string
    '''
    l_cut = selection.split('&&')

    log.warning('The following cuts remove all candidates')
    for cut in l_cut:
        res = rdf.Filter(cut)
        val = res.Count().GetValue()
        if val == 0:
            _print_values(rdf=rdf, cut=cut, number=20)
            log.info(cut)
# --------------------------
@pytest.mark.parametrize('sample', _RK_MISIDSAMPLES)
def test_nopid(sample : Component):
    '''
    Tests truth matching for noPID samples
    '''
    trigger = Trigger.rk_ee_nopid
    cut     = tm.get_truth(component = sample, project = trigger.project)

    with RDFGetter.max_entries(value = -1):
        gtr   = RDFGetter(sample=sample, trigger=trigger)
        d_rdf = gtr.get_rdf(per_file=True)

    fail = False
    for path, rdf_org in d_rdf.items():
        ini = rdf_org.Count().GetValue()
        rdf = rdf_org.Filter(cut, 'truth match')
        try:
            fin = rdf.Count().GetValue()
        except Exception as exc: 
            raise RuntimeError(f'Cannot apply cut: "{cut}"') from exc

        this_fail = 20 * fin < ini
        if this_fail:
            log.error('')
            log.error(path)
            log.error(f'{ini} ---> {fin}')
        else:
            log.debug('')
            log.debug(path)
            log.debug(f'{ini} ---> {fin}')

        fail = fail or this_fail

    assert not fail
# --------------------------
@pytest.mark.parametrize('sample', l_sample_kpee)
def test_bukee(sample : Component):
    '''
    Tests truth matching
    '''
    trigger = Trigger.rk_ee_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    ini = rdf.Count().GetValue()
    rdf = rdf.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        raise ValueError(f'Got no entries for {sample} and cut {cut}')

    assert 20 * fin > ini
# --------------------------
@pytest.mark.parametrize('sample', l_sample_kpmm)
def test_bukmm(sample : Component):
    '''
    Tests truth matching
    '''
    trigger = Trigger.rk_mm_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    ini = rdf.Count().GetValue()
    rdf = rdf.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    assert 20 * fin > ini
# --------------------------
@pytest.mark.parametrize('sample', l_sample_kstee)
def test_bdkstee(sample : Component):
    '''
    Tests truth matching
    '''
    trigger = Trigger.rkst_ee_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    assert 20 * fin > ini

    log.info(f'eff={fin/ini=:.3f}')
# --------------------------
@pytest.mark.parametrize('sample', l_sample_kstmm)
def test_bdkstmm(sample : Component):
    '''
    Tests truth matching
    '''
    trigger = Trigger.rkst_mm_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    assert 20 * fin > ini
    log.info(f'eff={fin/ini=:.3f}')
# --------------------------
@pytest.mark.parametrize('sample', l_sample_custom)
def test_custom(sample : Component):
    '''
    Test truth matching for custom samples, e.g. cocktails
    swapped tracks, etc
    '''
    trigger = Trigger.rkst_ee_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    assert 20 * fin > ini
    log.info(f'eff={fin/ini=:.3f}')
# --------------------------
@pytest.mark.parametrize('sample', _SEMILEPTONIC_SAMPLES_RK)
def test_semileptonic_rk(sample : Component):
    '''
    Test truth matching for custom samples, e.g. cocktails
    swapped tracks, etc
    '''
    trigger = Trigger.rk_ee_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    assert 20 * fin > ini
    log.info(f'eff={fin/ini=:.3f}')
# --------------------------
@pytest.mark.parametrize('sample', _SEMILEPTONIC_SAMPLES_RKST)
def test_semileptonic_rkst(sample : Component):
    '''
    Test truth matching for custom samples, e.g. cocktails
    swapped tracks, etc
    '''
    trigger = Trigger.rkst_ee_os
    cut     = tm.get_truth(component = sample, project = trigger.project)

    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    assert 20 * fin > ini
    log.info(f'Candidates: {ini} -> {fin}')
    log.info(f'eff={fin/ini=:.3f}')
# --------------------------
@pytest.mark.parametrize('sample, trigger', _EMULATED)
def test_emulated(sample : Component, trigger : Trigger):
    '''
    Tests with emulated samples 
    '''
    cut = tm.get_truth(component = sample, project = trigger.project)
    gtr = RDFGetter(sample=sample, trigger=trigger)
    org = gtr.get_rdf(per_file=False)

    ini = org.Count().GetValue()
    rdf = org.Filter(cut, 'truth match')
    fin = rdf.Count().GetValue()

    if fin == 0:
        _check_rdf(rdf=org, selection=cut)

    log.info(f'{sample}; eff={fin}/{ini}={fin/ini=:.3f}')

    assert fin > 0 
# --------------------------
