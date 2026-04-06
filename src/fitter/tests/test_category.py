'''
Module with tests for the Category class
'''
import pytest

from fitter      import Category
from dmu         import LogStore
from dmu.stats   import Model
from dmu.testing import get_model
from rx_common   import Block, Brem, Cuts

log=LogStore.add_logger('fitter:test_category')
# ----------------------
def test_simple():
    '''
    Simplest test
    '''
    pdf = get_model(kind = 'signal')
    cat = Category(
        name      = 'category',
        pdf       = pdf,
        sumw      = 1000.,
        model     = [Model.gauss],
        selection = {Cuts.mass : '(1)'})

    assert cat.pdf == pdf

    print(cat)
# ----------------------
@pytest.mark.parametrize('brem' , Brem)
@pytest.mark.parametrize('block', Block.blocks())
def test_properties(brem : Brem, block : Block):
    '''
    Tests that properties are calculated correctly
    '''
    pdf = get_model(kind = 'signal')
    cat = Category(
        name      = f'brem_{brem}_b{block}',
        pdf       = pdf,
        sumw      = 1000.,
        model     = [Model.gauss],
        selection = {Cuts.mass : '(1)'})

    assert cat.brem == brem
    assert cat.block== block 
# ----------------------
