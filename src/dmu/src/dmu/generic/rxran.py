'''
Module with functions needed to handle random numbers
'''
import numpy
import random

from contextlib import contextmanager
from dmu        import LogStore
from dmu.stats  import zfit

log=LogStore.add_logger('rx_generic:rxran')
# ----------------------
def _rseed_from_int(a : int, b : int) -> int:
    '''
    Parameters
    -------------
    a/b: Integers meant to be used to define a random seed

    Returns
    -------------
    Integer resulting from an injective ZxZ -> Z function. I.e. a Cantor pairing
    '''
    x = a + b

    y = x * (x + 1) / 2.

    return int(y + b)
# ----------------------
@contextmanager
def seed(
    value : int,
    index : int | None = None):
    '''
    Context manager used to set random seed

    Parameters
    -------------
    value: Random seed value, e.g. 42
    index: If doing an ensemble of datasets, value would identify the ensemble, index
           would identify the dataset. If None (default) the random seed is `value`
    '''
    if index is None:
        rseed = value
    else:
        rseed = _rseed_from_int(a = value, b = index)

    zfit.settings.set_seed(rseed)
    numpy.random.seed(rseed)
    random.seed(rseed)

    log.debug(f'Setting random seed to: {rseed}')

    try:
        yield
    finally:
        zfit.settings.set_seed()
        numpy.random.seed()
        random.seed()
