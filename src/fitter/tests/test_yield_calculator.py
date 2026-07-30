'''
Module holding tests for YieldCalculator
'''
from fitter    import YieldCalculator
from rx_common import Project

def test_simple():
    '''
    Simplest test
    '''

    ctr = YieldCalculator(
        name    = 'rare',
        project = Project.rk)

    grid = ctr.calculate()
