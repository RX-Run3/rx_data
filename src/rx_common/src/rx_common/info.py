'''
This script contains functions needed to get information on samples
'''

from ROOT        import RDF # type: ignore
from dmu         import LogStore
from dmu.generic import utilities  as gut
from .types      import Channel, Project, Trigger

_triggers = gut.load_data(package='rx_common_data', fpath='triggers.yaml')

log=LogStore.add_logger('rx_common:info')
# ----------------------
def is_rdf_data(rdf : RDF.RNode) -> bool:
    '''
    Parameters
    -------------
    rdf: ROOT dataframe

    Returns
    -------------
    True if it is real data, false for MC
    '''
    log.debug('Checking for data')

    names = [ name.c_str() for name in rdf.GetColumnNames() ]
    trueid= [ name         for name in names if name.endswith('TRUEID')]

    return not trueid
# ---------------------------------
def is_mc(sample : str) -> bool:
    '''
    Given a sample name, it will check if it is MC or data
    '''

    if sample.startswith('DATA'):
        return False

    return True
# ---------------------------------
def channel_from_trigger(trigger : str, lower_case : bool = False) -> str:
    '''
    Parameters
    ----------------
    trigger: Hlt2 trigger name, e.g. HLT2_BuKp...
    lower_case: If False (default), returns EE/MM, etc. Otherwise ee/mm, etc.

    Returns
    ----------------
    Channel, i.e. EE, MM, EM
    '''
    for project in _triggers:
        for channel in _triggers[project]:
            if trigger not in _triggers[project][channel]:
                continue

            if lower_case:
                return channel.lower()

            return channel

    raise ValueError(f'Trigger {trigger} not found')
# ---------------------------------
def is_ee(trigger : str) -> bool:
    '''
    Given Hlt2 trigger name, it will tell if it belongs to electron sample
    '''

    return channel_from_trigger(trigger) == 'EE'
# ---------------------------------
def is_mm(trigger : str) -> bool:
    '''
    Given Hlt2 trigger name, it will tell if it belongs to muon sample
    '''

    return channel_from_trigger(trigger) == 'MM'
# ---------------------------------
def is_em(trigger : str) -> bool:
    '''
    Given Hlt2 trigger name, it will tell if it belongs to electron-muon sample
    '''

    return channel_from_trigger(trigger) == 'MM'
# ---------------------------------
def project_from_trigger(trigger : str, lower_case : bool) -> str:
    '''
    Parameters
    -------------------
    trigger  : HLT2 trigger
    lowe_case: If True will return rk, rkst, etc

    Returns
    -------------------
    Project, e.g RK, RKst
    '''
    for project in _triggers:
        for channel in _triggers[project]:
            if trigger not in _triggers[project][channel]:
                continue

            if lower_case:
                return project.lower()

            return project

    raise ValueError(f'Trigger {trigger} not found')
# ---------------------------------
def get_trigger(
    project : Project, 
    kind    : str,
    channel : Channel) -> Trigger:
    '''
    Parameters
    --------------
    project: E.g. RK 
    channel: E.g. EE
    kind   : E.g. OS, SS, NOPID

    Returns
    --------------
    Hlt2 trigger enum 
    '''
    if project not in _triggers:
        raise ValueError(f'Invalid project: {project}')

    if channel not in _triggers[project]:
        raise ValueError(f'Invalid channel: {channel}')

    triggers = _triggers[project][channel]

    if kind == 'SS':
        [trigger] = [ value for value in triggers if value.endswith('SameSign_MVA') ]
        return Trigger(trigger)

    if kind == 'OS':
        [trigger] = [ value for value in triggers if value.endswith(f'{channel}_MVA') ]
        return Trigger(trigger)

    if kind == 'NOPID':
        [trigger] = [ value for value in triggers if value.endswith('_MVA_noPID') ]
        return Trigger(trigger)

    raise NotImplementedError(f'Invalid kind of trigger: {kind}')
# ---------------------------------
def is_reso(q2bin : str) -> bool:
    '''
    Takes q2bin name, returns true if it has associated
    charmonium component. If not, returns false.
    '''
    reso = ['jpsi', 'psi2']
    rare = ['low', 'cen_low', 'central', 'cen_high', 'high']

    if q2bin in reso:
        return True

    if q2bin in rare:
        return False

    raise ValueError(f'Invalid q2bin: {q2bin}')
