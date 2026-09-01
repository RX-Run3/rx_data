'''
Module with tests for PrecMaker class
'''
from hqm.config     import TransferFunctionMakerConf
from hqm.prec_maker import PrecMaker
from rx_common      import Trigger, Qsq

def test_simple():
    '''
    Simplest test
    '''
    trig = Trigger.rk_ee_os

    cfg = TransferFunctionMakerConf.load(
        variable = 'none',
        project  = trig.project,
        source   = Qsq.jpsi,
        target   = Qsq.jpsi)

    obj = PrecMaker(cfg = cfg[0], trigger = trig)
    pdf = obj.get_pdf()
