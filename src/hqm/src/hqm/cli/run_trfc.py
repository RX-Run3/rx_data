'''
Script used to steer creation of transfer functions
'''
import typer

from dmu        import LogStore
from rx_common  import Project, Qsq
from hqm.types  import Mode
from typing     import Final
from .make_trfc import make_trfc

_BLOCKS   : Final[list[int]]             = list(range(1, 9))
_MODE     : Final[Mode]                  = Mode.reuse
_PROJECTS : Final[list[Project]]         = [Project.rk]
_COMBOS   : Final[list[tuple[Qsq, Qsq]]] = [
    (Qsq.jpsi, Qsq.jpsi),
    (Qsq.jpsi, Qsq.psi2),
    (Qsq.psi2, Qsq.jpsi),
    (Qsq.psi2, Qsq.psi2),
    (Qsq.psi2, Qsq.high),
]

bin_opt = typer.Option('', '-b', help='String defining binning, e.g. "mva_cmb-1 mva_prc-3"')

log=LogStore.add_logger('hqm:run_trfc')
# ----------------------
def run_trfc(binning: str = bin_opt):
    '''
    Run fits to electron channel simulation to extract transfer functions
    '''
    total = len(_BLOCKS) * len(_PROJECTS) * len(_COMBOS)
    index = 0

    for block in _BLOCKS:
        b_arg = f'block-{block}'
        if binning:
            b_arg = f'{b_arg} {binning}'

        for project in _PROJECTS:
            for source, target in _COMBOS:
                index += 1
                log.info(f'[Progress: {index}/{total}] block: {block}, project: {project}, -s {source} -t {target}')
                make_trfc(
                    mode    = _MODE,
                    binning = b_arg,
                    project = project,
                    source  = source,
                    target  = target,
                )
