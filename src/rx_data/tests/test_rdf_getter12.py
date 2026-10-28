'''
Script used to test RDFGetter12 class
'''


import pytest

from typing   import Final
from ROOT     import RDF
from dmu      import LogStore
from rx_data  import RDFGetter12

log=LogStore.add_logger('rx_data:test_rdf_getter12')

_DATASETS : Final[list[str]] = ['2011', '2012', '2015', '2016', '2017', '2018', 'all']
_SAMPLES  : Final[list[str]] = ['Bu_Kee_eq_btosllball05_DPC']
# ---------------------------------------------
def _check_rdf(rdf : RDF.RNode, name : str) -> None:
    nentries = rdf.Count().GetValue()

    assert nentries > 0

    log.info('')
    log.info(f'{name:<40}{nentries:<15}')
# ---------------------------------------------
@pytest.mark.parametrize('sample',  _SAMPLES)
@pytest.mark.parametrize('dset'  , _DATASETS)
def test_simple(sample : str, dset : str):
    '''
    Simplest test
    '''
    trigger = 'Hlt2RD_BuToKpEE_MVA' if 'ee_eq' in sample else 'Hlt2RD_BuToKpMuMu_MVA'

    gtr = RDFGetter12(
        sample =sample,
        trigger=trigger,
        dset   =dset)

    rdf = gtr.get_rdf()

    _check_rdf(rdf=rdf, name = f'simple_{sample}_{dset}')
# ---------------------------------------------
@pytest.mark.parametrize('sample',  _SAMPLES)
@pytest.mark.parametrize('dset'  , _DATASETS)
def test_add_selection(sample : str, dset : str):
    '''
    Simplest test
    '''
    trigger = 'Hlt2RD_BuToKpEE_MVA' if 'ee_eq' in sample else 'Hlt2RD_BuToKpMuMu_MVA'
    d_sel   = {
        'bdt' : 'mva_cmb > 0.5 & mva_prc > 0.5',
        'q2'  : 'q2_track > 14300000'}

    with RDFGetter12.add_selection(d_sel = d_sel):
        gtr = RDFGetter12(
            sample =sample,
            trigger=trigger,
            dset   =dset)

        rdf = gtr.get_rdf()

    _check_rdf(rdf=rdf, name = f'simple_{sample}_{dset}')
# ---------------------------------------------
