'''
Module with functionality specifying how to process the data
'''
from contextlib  import contextmanager
from contextvars import ContextVar

# -----------------------------
nproc : ContextVar[None|int] = ContextVar('nproc', default = None)
@contextmanager
def set_nproc(value : int):
    '''
    '''
    if nproc.get() is not None:
        raise ValueError('Number of processes already set')

    token = nproc.set(value)

    try:
        yield
    finally:
        nproc.reset(token)
# -----------------------------
def get_nproc() -> int:
    '''
    Number of processes allowed
    '''
    val = nproc.get()

    if val is None:
        raise ValueError('Number of processes was not set')

    return val
# -----------------------------
