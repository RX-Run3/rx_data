'''
Script used to steer running resonant fits
'''
import typer

from rx_common     import Project
from dmu.generic   import Mode
from typing        import Final
from .fit_resonant import fit_resonant

_MODE     : Final[Mode]          = Mode.reuse
_PROJECTS : Final[list[Project]] = [Project.rk]

bin_opt = typer.Option('', '-b', help='Binning, e.g. "block-1 mva_cmb-7 mva_prc-7"')

def run_ratios(binning: str = bin_opt):
    '''
    Run simultaneous fit to resonant modes across blocks and projects
    '''
    for project in _PROJECTS:
        fit_resonant(
            mode    = _MODE,
            binning = binning,
            project = project,
        )
