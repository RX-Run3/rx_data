'''
Script used to steer running resonant fits
'''
import typer

from rx_common     import Project
from hqm.types     import Mode
from typing        import Final
from .fit_resonant import fit_resonant

_BLOCKS   : Final[list[int]]     = list(range(1, 9))
_MODE     : Final[Mode]          = Mode.reuse
_PROJECTS : Final[list[Project]] = [Project.rk]

bin_opt = typer.Option('', '-b', help='Binning, e.g. "mva_cmb-7 mva_prc-7"')

def run_ratios(binning: str = bin_opt):
    '''
    Run simultaneous fit to resonant modes across blocks and projects
    '''
    for block in _BLOCKS:
        for project in _PROJECTS:
            b_str = f'block-{block}'
            if binning:
                b_str = f'{b_str} {binning}'

            fit_resonant(
                mode    = _MODE,
                binning = b_str,
                project = project,
            )
