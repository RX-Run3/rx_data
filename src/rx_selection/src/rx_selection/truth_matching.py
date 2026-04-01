'''
Module containing functions used for truth matching
'''

from dmu               import LogStore
from dmu.generic       import utilities as gut
from dmu.yaml.resolver import Resolver
from rx_common         import Component

log=LogStore.add_logger('rx_selection:truth_matching')
# ----------------------
def get_truth(component : Component, kind : str) -> str:
    r'''
    Parameters:
    --------------------------
    component : MC component, representing process 
    kind      : Either bukll or bdkstll

    Returns:
    --------------------------
    For data it will return '(1)'. For MC, truth matching string. 
    The truth matching string will assume that the candidates were reconstructed as:

    kind = bdkstll -> $B^0\to K^* e^+e^-$ candidates
    kind = bukll   -> $B^+\to K^+ e^+e^-$ candidates
    '''
    if not component.is_mc:
        return '(1)'

    cfg = gut.load_conf(package='rx_selection_data', fpath=f'truth_matching/{kind}.yaml')
    yrs = Resolver(cfg=cfg)

    if component.event_type not in yrs:
        raise KeyError(f'Could not find event type {component.event_type} in config')

    requirement = yrs[component.event_type]

    log.debug(f'Using truth matching: {requirement}')

    return requirement
# ----------------------------------------------------------

