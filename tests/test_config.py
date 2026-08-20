'''
Module with tests for Config class
'''

from rx_common  import Qsq
from hqm.config import TransferFunctionMakerConf
from hqm.config import CCbarRatioCalculatorConf 

#----------------------------------
def test_unbinned_trfc():
    '''
    Test configuration loader for unbinned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        variable = 'none',
        source   = Qsq.psi2,
        target   = Qsq.high)

    assert len(cfgs) == 1

    print(cfgs[0])
#----------------------------------
def test_binned_trfc():
    '''
    Test configuration loader for binned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        variable = 'nbrem',
        source   = Qsq.psi2,
        target   = Qsq.high)

    assert len(cfgs) > 1

    for cfg in cfgs:
        print(cfg)
#----------------------------------
def test_unbinned_ratio():
    '''
    Test unbinned ratio calculator configuration
    '''
    cfgs = CCbarRatioCalculatorConf.load(variable = 'none')

    assert len(cfgs) == 1

    print(cfgs[0])
#----------------------------------
def test_binned_ratio():
    '''
    Test configuration loader for binned case
    '''
    cfgs = CCbarRatioCalculatorConf.load(variable = 'nbrem')
    assert len(cfgs) > 1

    for cfg in cfgs:
        print(cfg)
#----------------------------------
