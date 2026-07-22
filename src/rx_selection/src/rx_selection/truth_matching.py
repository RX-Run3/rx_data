'''
Module containing functions used for truth matching
'''

from dmu               import LogStore
from dmu.generic       import utilities as gut
from dmu.yaml.resolver import Resolver
from rx_common         import Component, Project

log=LogStore.add_logger('rx_selection:truth_matching')
# ----------------------
def get_truth(component : Component, project : Project) -> str:
    r'''
    Parameters:
    --------------------------
    component : MC component, representing process 
    project   : Either rk or rkst

    Returns:
    --------------------------
    For data it will return '(1)'. For MC, truth matching string. 
    The truth matching string will assume that the candidates were reconstructed as:

    rk   -> $B^+\to K^+ e^+e^-$ candidates
    rkst -> $B^0\to K^* e^+e^-$ candidates
    '''
    if not component.is_mc:
        return '(1)'

    cfg = gut.load_conf(package='rx_selection_data', fpath=f'truth_matching/{project}.yaml')
    yrs = Resolver(cfg=cfg)

    if component.event_type not in yrs:
        raise KeyError(f'Could not find event type {component.event_type} in config')

    requirement = yrs[component.event_type]

    log.debug(f'Using truth matching: {requirement}')

    return requirement
# ----------------------------------------------------------

