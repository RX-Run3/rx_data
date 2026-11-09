'''
File holding tests for Block Enum
'''
import pytest

from rx_common import Block
from dmu       import LogStore

log=LogStore.add_logger('rx_common::test_block')
# -------------------------------------------
def test_block_is_composite():
    '''
    Test block is_composite
    '''
    b1  = Block(value = 1)
    b12 = Block(value = {1, 2})

    assert not b1.is_composite
    assert b12.is_composite
# -------------------------------------------
def test_block_sub_blocks():
    '''
    Test block sub_blocks property
    '''
    b1  = Block(value = 1)
    b12 = Block(value = {1, 2})

    assert b1.sub_blocks == [b1]
    assert set(b12.sub_blocks) == {b1, Block(value = 2)}
# -------------------------------------------
def test_block():
    '''
    Test block class
    '''
    for block in range(1, 9):
        Block(value = block)

    with pytest.raises(ValueError):
        Block(value = 11)

    with pytest.raises(ValueError):
        Block(value = 10)

    b1 = Block(value = 1)
    b2 = Block(value = 2)

    assert (b1 + b2) == Block(value = {1, 2})
    assert '1'       == str(b1)
    assert '2'       == str(b2)
    assert '12'      == str(b1 + b2)

    assert Block(value = -1).to_int() == -1
# -------------------------------------------
def test_block_from_str():
    '''
    Test block class
    '''
    for val in range(1, 9):
        assert Block.from_str(value = str(val)).to_int() == val

    assert Block.from_str(value = 'all').to_int() == -1
# -------------------------------------------
def test_block_dump():
    '''
    Test block class
    '''
    for block in range(1, 9):
        data = Block(value = block).model_dump()
        print(data)
# -------------------------------------------
@pytest.mark.parametrize('value', [1, 2, {2, 3}])
def test_hash(value : int | set[int]):
    '''
    Test hashing block
    '''
    block = Block(value = value)

    hash(block)
# -------------------------------------------
def test_block_lt():
    '''
    Test block less than comparison
    '''
    b1   = Block(value = 1)
    b2   = Block(value = 2)
    b12  = Block(value = {1, 2})
    ball = Block(value = -1)

    assert     b1 < b2
    assert not b2 < b1
    assert    ball< b12
# -------------------------------------------
