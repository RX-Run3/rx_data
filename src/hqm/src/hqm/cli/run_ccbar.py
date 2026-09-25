import typer

from rx_common   import Project
from dmu.generic import Mode
from typing      import Final
from .make_ccbar import make_ccbar

_MODE     : Final[Mode]          = Mode.reuse
_PROJECTS : Final[list[Project]] = [Project.rk]

bin_opt = typer.Option('', '-b', help='Binning, e.g. "block-1 mva_cmb-3 mva_prc-2"')

def run_ccbar(binning: str = bin_opt):
    '''
    Run ccbar generation across blocks and projects
    '''
    for project in _PROJECTS:
        make_ccbar(
            mode    = _MODE,
            binning = binning,
            project = project,
        )
