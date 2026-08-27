'''
Module with tests for Qsq enum
'''
from rx_common import Qsq

def test_bounds():
    '''
    Tests q2 bound retrieval
    '''
    for qsq in Qsq:
        print(qsq.upper_bound)
        print(qsq.lower_bound)
