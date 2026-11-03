'''
This module contains functions meant to be shared by code in rx_efficiencies
'''
from typing    import Final
from rx_common import Project, Component

_BOTH        : Final[list[Component]] = [
    # ----
    # Kpi ll
    # ----
    Component.bdkstkpiee,
    Component.bdkstkpimm,
]
_RK          : Final[list[Component]] = [
    # ----
    # K ll
    # ----
    Component.bpkstkpiee,
    Component.bpkpee,
    Component.bpkpmm,
    Component.bpkpjpsiee,
    Component.bpkpjpsimm,
    Component.bpkppsi2ee,
    Component.bpkppsi2mm,
    # ----
    # pi ll
    # ----
    Component.bppijpsiee,
    Component.bppijpsimm,
    # ----
    # KK ll
    # ----
    Component.bsphiee,
]
_RKST        : Final[list[Component]] = [
    # ----
    # Kpipi ll
    # ----
    Component.bpk1kpipiee,
    Component.bpk2kpipiee,
    # ----
    # Kpi ll
    # ----
    Component.bdkstkpijpsiee,
    Component.bdkstkpijpsimm,
    Component.bdkstkpipsi2ee,
    Component.bdkstkpipsi2mm,
    Component.bskstjpsiee,
    Component.bskstjpsimm,
    Component.bskstpsi2ee,
    Component.bskstpsi2mm,
    # ----
    # KK ll
    # ----
    Component.bsphijpsiee,
    Component.bsphijpsimm,
    # ----
    # pK ll
    # ----
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
