'''
Module with functions testing MisCalculator
'''
import pytest

from ROOT        import RDF
from dmu         import LogStore
from rx_data     import MisCalculator
from rx_data     import testing       as tst

log=LogStore.add_logger('rx_data:test_mis_calculator')
# ------------------------
class Data:
    '''
    Class used to share attributes
    '''
    l_must_have_bplus = ['L1_PE', 'L2_PE', 'H_PE']
    l_must_have_bzero = ['L1_PE', 'L2_PE', 'H1_PE', 'H2_PE']
# ------------------------
def _check_rdf(rdf : RDF.RNode, l_must_have : list[str]) -> None:
    l_name = [ name.c_str() for name in rdf.GetColumnNames() ]

    success = True
    for must_have in l_must_have:
        if must_have not in l_name:
            success = False
            log.warning(f'Missing {must_have}')

    assert success
# ------------------------
@pytest.mark.parametrize('prefix, kind', tst.l_prefix_kind)
def test_simple(kind : str, prefix : str):
    '''
    Simplest test of class
    '''
    trigger = tst.get_trigger(kind = kind, prefix = prefix)
    rdf = tst.get_rdf(kind=kind, prefix=prefix)
    cal = MisCalculator(rdf=rdf, trigger=trigger)
    rdf = cal.get_rdf()

    if 'B0ToKpPim' in prefix:
        l_must_have = Data.l_must_have_bzero
    elif 'BuToKp' in prefix:
        l_must_have = Data.l_must_have_bplus
    else:
        raise ValueError(f'Invalid preffix: {prefix}')

    _check_rdf(rdf=rdf, l_must_have=l_must_have)
