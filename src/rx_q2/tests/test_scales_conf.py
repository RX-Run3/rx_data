'''
Module with tests for ScalesConf
'''
from rx_common import MVAWp
import pytest

from rx_common   import Trigger
from rx_q2       import ScalesConf
from dmu.generic import utilities as gut

@pytest.mark.parametrize('name', ['scales_B', 'scales_q2'])
def test_simple(name : str):
    '''
    Simples test
    '''
    data = gut.load_data(
        package = 'rx_q2_data',
        fpath   = f'plots/{name}.yaml')

    mva = MVAWp(root = 0.5)

    data['name'] = 'reso_no_dtf'
    data['kind'] = 'q2'
    data['comb'] = mva
    data['prec'] = mva
    data['trig'] = Trigger.rk_ee_os
    data['year'] = '2024'

    ScalesConf(**data)
