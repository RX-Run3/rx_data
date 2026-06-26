'''
This module contains functions meant to be shared by code in rx_efficiencies
'''
from typing    import Final
from rx_common import Project, Component

_BOTH        : Final[list[Component]] = [
    Component.bdkstkpiee,
    Component.bdkstkpimm,
]
_RK          : Final[list[Component]] = [
    Component.bpkpee,
    Component.bpkpmm,
    Component.bpkpjpsiee,
    Component.bpkpjpsimm,
    Component.bpkppsi2ee,
    Component.bpkppsi2mm,
    Component.bppijpsiee,
    Component.bppijpsimm,
    Component.bsphiee,
]
_RKST        : Final[list[Component]] = [
    Component.bpkstkpiee,
    Component.bpk1kpipiee,
    Component.bpk2kpipiee,
    Component.bdkstkpijpsiee,
    Component.bdkstkpijpsimm,
    Component.bdkstkpipsi2ee,
    Component.bdkstkpipsi2mm,
    Component.bsphijpsiee,
    Component.bsphijpsimm,
    Component.lbpkjpsiee,
    Component.lbpkjpsimm,
]
# ---------------------------------------
def is_acceptance_defined(sample : Component, project : Project) -> bool:
    '''
    Parameters
    -------------
    sample : MC sample, e.g. bpkpee
    project: E.g. rk or rkst

    Returns
    -------------
    True or false. False if for this project this samples' acceptance does not make sense 
    '''
    if project not in {Project.rk, Project.rkst}:
        raise ValueError(f'Invalid project: {project}')

    all_samples = _BOTH + _RK + _RKST
    if sample not in all_samples:
        raise ValueError(f'Unrecognized sample: {sample}')

    if project == Project.rk   and sample in _RKST:
        return False 

    if project == Project.rkst and sample in _RK:
        return False 

    return True 
# ---------------------------------------
