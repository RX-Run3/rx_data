import typer

from rx_common   import Project
from hqm.types   import Mode
from typing      import Final
from .make_ccbar import make_ccbar

_BLOCKS   : Final[list[int]]     = list(range(1, 9))
_MODE     : Final[Mode]          = Mode.reuse
_PROJECTS : Final[list[Project]] = [Project.rk]

bin_opt = typer.Option('', '-b', help='Binning, e.g. "mva_cmb-3 mva_prc-2"')

def run_ccbar(binning: str = bin_opt):
    '''
    Run ccbar generation across blocks and projects
    '''
    for block in _BLOCKS:
        for project in _PROJECTS:
            b_str = f'block-{block}'
            if binning:
                b_str = f'{b_str} {binning}'

            make_ccbar(
                mode    = _MODE,
                binning = b_str,
                project = project,
            )

        return

