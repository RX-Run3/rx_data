'''
Script used to steer creation of databases
'''

from rx_common       import Trigger, Component
from typing          import Final
from .build_database import build_database

_ITEMS: Final[list[tuple[Trigger, Component]]] = [
    (Trigger.rkst_mm_os, Component.bdkstkpipsi2mm),
    (Trigger.rkst_ee_os, Component.bdkstkpipsi2ee),
    (Trigger.rkst_mm_os, Component.bdkstkpijpsimm),
    (Trigger.rkst_ee_os, Component.bdkstkpijpsiee),
    (Trigger.rkst_mm_os, Component.data_24       ),
    (Trigger.rkst_ee_os, Component.data_24       ),
    (Trigger.rk_mm_os  , Component.bpkpjpsimm    ),
    (Trigger.rk_ee_os  , Component.bpkpjpsiee    ),
    (Trigger.rk_mm_os  , Component.bpkppsi2mm    ),
    (Trigger.rk_ee_os  , Component.bpkppsi2ee    ),
    (Trigger.rk_mm_os  , Component.data_24       ),
    (Trigger.rk_ee_os  , Component.data_24       ),
]

def run_databases() -> None:
    '''
    Run build-database across predefined tag and channel pairs
    '''
    for trigger, comp in _ITEMS:
        build_database(
            trigger = trigger,
            comp    = comp)
