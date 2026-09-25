'''
Script used to steer running MC fits
'''
import typer

from dmu       import LogStore
from rx_common import Component, Trigger, Qsq
from dmu.generic import Mode
from typing    import Final
from .fit_mc   import fit_mc

_MODE     : Final[Mode]                            = Mode.reuse
_PAIRS    : Final[list[tuple[Component, Trigger]]] = [
    (Component.bpkpjpsiee, Trigger.rk_ee_os),
    (Component.bpkppsi2ee, Trigger.rk_ee_os),
    (Component.bpkpjpsimm, Trigger.rk_mm_os),
    (Component.bpkppsi2mm, Trigger.rk_mm_os),
]

_JPSI_EE  : Final[list[Component]] = [Component.bpkpjpsiee, Component.bdkstkpijpsiee]
_PSI2_EE  : Final[list[Component]] = [Component.bpkppsi2ee, Component.bdkstkpipsi2ee]
_HIGH_EE  : Final[list[Component]] = []

_JPSI_MM  : Final[list[Component]] = [Component.bpkpjpsimm, Component.bdkstkpijpsimm]
_PSI2_MM  : Final[list[Component]] = [Component.bpkppsi2mm, Component.bdkstkpipsi2mm]
_HIGH_MM  : Final[list[Component]] = []

_QSQBINS  : Final[list[Qsq]] = [Qsq.jpsi, Qsq.psi2, Qsq.high]

binning_opt = typer.Option('', '-b', help='E.g. "block-1 mva_cmb-7 mva_prc-3"')

log=LogStore.add_logger('hqm:run_fits')
# --------------------------------------------
def _in_resonant(q2bin: Qsq, component: Component) -> bool:
    in_jpsi = q2bin == Qsq.jpsi and component in _JPSI_EE
    in_psi2 = q2bin == Qsq.psi2 and component in _PSI2_EE

    return in_jpsi or in_psi2
# --------------------------------------------
def _skip_fit(q2bin: Qsq, component: Component, trigger: Trigger) -> bool:
    if q2bin == Qsq.high and component in _JPSI_EE:
        return True

    if trigger.is_electron:
        return False

    if q2bin == Qsq.jpsi and component not in _JPSI_MM:
        return True

    if q2bin == Qsq.psi2 and component not in _PSI2_MM:
        return True

    if q2bin == Qsq.high and component not in _HIGH_MM:
        return True

    return False
# --------------------------------------------
def _run_fit_mc(component: Component, trigger: Trigger, q2bin: Qsq, binning: str) -> None:
    is_leakage = not _in_resonant(q2bin, component)
    if is_leakage:
        fit_mc(
            component = component,
            trigger   = trigger,
            qsq       = q2bin,
            use_dtf   = False,
            use_kde   = False,
            smear     = True,
            binning   = binning,
            mode      = _MODE,
        )
    else:
        fit_mc(
            component = component,
            trigger   = trigger,
            qsq       = q2bin,
            use_dtf   = True,
            use_kde   = False,
            smear     = True,
            binning   = binning,
            mode      = _MODE,
        )
        fit_mc(
            component = component,
            trigger   = trigger,
            qsq       = q2bin,
            use_dtf   = False,
            use_kde   = True,
            smear     = True,
            binning   = binning,
            mode      = _MODE,
        )
# --------------------------------------------
def run_fits(binning: str = binning_opt):
    '''
    Runs fits for a given bin
    '''
    for component, trigger in _PAIRS:
        for q2bin in _QSQBINS:

            if _skip_fit(q2bin, component, trigger):
                continue

            log.info(f'Iteration: {component}-{trigger}, q2bin {q2bin}')
            _run_fit_mc(component, trigger, q2bin, binning)
# --------------------------------------------
