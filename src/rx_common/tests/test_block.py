'''
File holding tests for Block Enum
'''
import pytest

from rx_common import Block
from dmu       import LogStore

log=LogStore.add_logger('rx_common::test_block')
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
