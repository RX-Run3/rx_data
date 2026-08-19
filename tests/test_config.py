'''
Module with tests for Config class
'''

from rx_common  import Qsq
from hqm.config import Conf

#----------------------------------
def test_simple():
    cfg = Conf.load(
        name   = 'transfer',
        source = Qsq.psi2,
        target = Qsq.high)

    print(cfg)
#----------------------------------
