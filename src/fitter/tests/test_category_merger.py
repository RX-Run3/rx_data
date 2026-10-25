'''
Module used to test CategoryMerger class
'''
import pytest

from dmu         import LogStore
from dmu.stats   import Model, zfit
from dmu.testing import get_model 
from fitter      import CategoryMerger
from fitter      import Category
from rx_common   import Brem, Block, Component, Cuts

zpdf = zfit.pdf.BasePDF
log  = LogStore.add_logger('fitter:test_category_merger')

BREM_012 = [ Brem.zero, Brem.one, Brem.two ]
BREM_01  = [ Brem.zero, Brem.one           ]
BREM_02  = [ Brem.zero, Brem.two           ]
BREM_12  = [ Brem.one , Brem.two           ]
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:category_merger', 10)
# ----------------------------------------
def _get_category(name : str) -> Category:
    '''
    Parameters
    -------------
    name: Name of category

    Returns
    -------------
    Category object
    '''
    obs = zfit.Space('mass', limits = (0, 10))
    pdf = get_model(
        obs    = obs,
        kind   = 'signal', 
        suffix = name)

    cat  = Category(
        name      = name, 
        pdf       = pdf, 
        sumw      = 1000., 
        selection = {Cuts.mass : '(1)'},
        model     = [Model.gauss])

    return cat
# ----------------------------------------
@pytest.mark.parametrize('brems', [BREM_012, BREM_01, BREM_02, BREM_12])
def test_add_brem(brems : list[Brem]):
    '''
    Add only brems for given block 
    '''
    log.info(f'Adding: {brems}')
    names      = [ f'{brem}_b1' for brem in brems ]
    categories = [ _get_category(name = name) for name in names ]

    mgr = CategoryMerger(
        reparametrize = True,
        categories    = categories, 
        comp          = Component.bpkpee)
    cat = mgr.get_category()

    assert isinstance(cat, Category)

    print(cat)
# ----------------------------------------
def test_add_block():
    '''
    Add only blocks for given brem
    '''
    names      = [ f'brem_xx1_b{block}' for block in range(1, 4) ]
    categories = [ _get_category(name = name) for name in names ]

    mgr = CategoryMerger(
        reparametrize = True,
        categories    = categories, 
        comp          = Component.bpkpee)
    cat = mgr.get_category()

    cat = mgr.get_category()

    assert isinstance(cat, Category)

    print(cat)
# ----------------------------------------
def test_add_brem_block():
    '''
    Add brems and then blocks
    '''
    names      = [ f'{brem}_b{block}' for block in Block.blocks() for brem in Brem.brems() ]
    categories = [ _get_category(name = name) for name in names ]

    mgr = CategoryMerger(
        reparametrize = True,
        categories    = categories, 
        comp          = Component.bpkpee)
    cat = mgr.get_category()

    log.info(cat)

    assert isinstance(cat, Category)
# ----------------------------------------
