'''
Module with tests for DatabaseBuilder class
'''

from rx_common            import Component, Qsq, Trigger
from hqm.database_builder import DatabaseBuilder, DatabaseBuilderConf

def test_simple():
    trig = Trigger.rk_ee_os
    comp = Component.bpkpjpsimm
    qsq  = Qsq.jpsi

    obj = DatabaseBuilder(
        trig = trig,
        comp = comp,
        qsq  = qsq)

    cfg = DatabaseBuilderConf.load()
    obj.run(cfg = cfg)
