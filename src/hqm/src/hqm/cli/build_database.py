'''
Module used to expose build_database function to CLI
'''
import typer

from rx_common            import Component, Trigger
from hqm.database_builder import DatabaseBuilder
from hqm.database_conf    import DatabaseConf

trig_opt = typer.Option(..., '-t', help = 'Hlt2 trigger, i.e. rk_ee_os')
comp_opt = typer.Option(..., '-c', help = 'Dataset, e.g. data_24')

def build_database(
    trigger : Trigger  = trig_opt,
    comp    : Component= comp_opt):
    '''
    Build database
    '''
    cfg = DatabaseConf.load()
    if cfg.has_output(comp = comp, trig = trigger):
        return

    obj = DatabaseBuilder(trig = trigger, comp = comp, cfg = cfg)
    obj.run()
