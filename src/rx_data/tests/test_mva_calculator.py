'''
Module containing tests for MVACalculator class
'''
import pytest
import matplotlib.pyplot as plt

from pathlib   import Path
from ROOT      import RDF
from dmu       import LogStore
from rx_data   import RDFGetter
from rx_data   import MVACalculator
from rx_common import Component, Trigger

log=LogStore.add_logger('rx_data:test_mva_calculator')
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    l_trigger= [Trigger.rk_mm_os, Trigger.rk_ee_os]
    nentries = 30_000
    version  = 'v8'
    l_mc     = [
        (Trigger.rk_ee_os, Component.bpkpee ),
        (Trigger.rk_mm_os, Component.bpkpmm )]

    l_nopid  = [(Trigger.rk_ee_nopid, Component.bpkpjpsiee)]
# ----------------------
def _validate_rdf(
    rdf     : RDF.RNode,
    name    : str,
    out_dir : Path) -> None:
    '''
    Parameters
    -------------
    rdf: ROOT dataframe with MVA scores
    '''
    log.info('Validating dataframe')

    nentries = rdf.Count().GetValue()
    assert nentries == Data.nentries

    log.info('Found columns:')
    for col_name in rdf.GetColumnNames():
        log.info(f'    {col_name}')

    log.info('Extracting data')
    data = rdf.AsNumpy()

    log.info('Plotting')

    plt.hist(data['mva_cmb'], bins=50, range=(-1,+1), histtype='step', label='Combinatorial')
    plt.hist(data['mva_prc'], bins=50, range=(-1,+1), histtype='step', label='Part reco')
    plt.savefig(f'{out_dir}/{name}.png')
    plt.close()
# ----------------------
@pytest.mark.parametrize('trigger', Data.l_trigger)
def test_data(trigger : Trigger, tmp_path : Path) -> None:
    '''
    Test MVACalculator with data
    '''
    sample = Component.data_24 
    with RDFGetter.max_entries(value=Data.nentries):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    cal = MVACalculator(
    rdf     = rdf,
    sample  = sample,
    trigger = trigger,
    version = Data.version)

    rdf = cal.get_rdf(kind = 'root')
    _validate_rdf(rdf=rdf, out_dir=tmp_path, name=f'data_{trigger}')
# --------------------------------
@pytest.mark.parametrize('trigger, sample', Data.l_mc)
def test_mc(trigger : Trigger, sample : Component , tmp_path : Path) -> None:
    '''
    Test MVACalculator with simulation
    '''
    with RDFGetter.max_entries(value=Data.nentries):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    cal = MVACalculator(
    rdf     = rdf,
    sample  = sample,
    trigger = trigger,
    version = Data.version)

    rdf = cal.get_rdf(kind = 'root')
    _validate_rdf(rdf=rdf, out_dir=tmp_path, name=f'{sample}_{trigger}')
# ----------------------
@pytest.mark.parametrize('trigger, sample', Data.l_mc)
def test_mc_noversion(trigger : Trigger, sample : Component, tmp_path : Path) -> None:
    '''
    Test MVACalculator with default (should be lates) version
    '''
    with RDFGetter.max_entries(value=Data.nentries):
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    cal = MVACalculator(
    rdf     = rdf,
    sample  = sample,
    trigger = trigger)

    rdf = cal.get_rdf(kind = 'root')
    _validate_rdf(rdf=rdf, out_dir=tmp_path, name=f'{sample}_{trigger}')
# --------------------------------
@pytest.mark.parametrize('trigger, sample', Data.l_nopid)
def test_nopid(trigger : Trigger, sample : Component, tmp_path : Path) -> None:
    '''
    Test MVACalculator with default (should be lates) version
    '''
    with RDFGetter.max_entries(value=Data.nentries),\
        RDFGetter.exclude_friends(names=['mva']):
        gtr = RDFGetter(sample=sample, trigger=trigger) 
        rdf = gtr.get_rdf(per_file=False)

    cal = MVACalculator(
    rdf     = rdf,
    sample  = sample,
    trigger = trigger)

    rdf = cal.get_rdf(kind = 'root')
    _validate_rdf(rdf=rdf, out_dir=tmp_path, name=f'{sample}_{trigger}')
# --------------------------------
