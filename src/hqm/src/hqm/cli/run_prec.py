'''
Script used to steer creation of part reco templates
'''
import typer

from rx_common  import Project, Qsq
from dmu        import LogStore
from hqm.types  import Mode
from typing     import Final
from .make_prec import make_prec

_BLOCKS   : Final[list[int]]     = list(range(1, 9))
_MODE     : Final[Mode]          = Mode.reuse
_PROJECTS : Final[list[Project]] = [Project.rk]
_SOURCES  : Final[list[Qsq]]     = [Qsq.jpsi, Qsq.psi2]
_TARGETS  : Final[list[Qsq]]     = [Qsq.jpsi, Qsq.psi2, Qsq.high]

binning_opt = typer.Option('', '-b', help='String specifying working point, e.g. "mva_cmb-7 mva_prc-6"')

log=LogStore.add_logger('hqm:run_prec')
# ----------------------
def run_prec(binning: str = binning_opt):
    '''
    Selects lower sideband in muon data, fits it to a non-parametric PDF, 
    and convolves it with transfer function to produce part-reco templates
    '''
    total = len(_BLOCKS) * len(_PROJECTS) * len(_SOURCES) * len(_TARGETS)
    index = 0

    for block in _BLOCKS:
        for project in _PROJECTS:
            for source in _SOURCES:
                for target in _TARGETS:
                    if source == Qsq.jpsi and target == Qsq.high:
                        continue

                    index  += 1
                    _binning = f'block-{block} {binning}'.strip()

                    log.info(f'[Progress: {index}/{total}] block: {block}, project: {project}, -s {source} -t {target}')
                    make_prec(
                        mode    = _MODE,
                        project = project,
                        source  = source,
                        target  = target,
                        binning = _binning,
                    )
        return
# ----------------------
