'''
Module with tests for Config class
'''

from rx_common  import Qsq
from hqm.config import TransferFunctionMakerConf

#----------------------------------
def test_unbinned():
    '''
    Test configuration loader for unbinned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        binning= 'none',
        source = Qsq.psi2,
        target = Qsq.high)

    assert len(cfgs) == 1

    print(cfgs[0])
#----------------------------------
def test_binned():
    '''
    Test configuration loader for binned case
    '''
    cfgs = TransferFunctionMakerConf.load(
        binning= 'brem',
        source = Qsq.psi2,
        target = Qsq.high)

    assert len(cfgs) > 1

    for cfg in cfgs:
        print(cfg)
#----------------------------------

