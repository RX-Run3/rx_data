'''
Module used to run fits to resonant mode data
'''
import typer
import numpy
import numpy.typing as npt
import matplotlib.pyplot as plt

from typing         import Final
from hqm.config     import CCbarRatioCalculatorConf
from hqm.data_store import DataStore
from hqm.ratc       import CCbarRatioCalculator
from hqm.types      import PRecRatio
from rx_common      import Block, Component, Project, Qsq, Cuts

binning_opt = typer.Option(...  , '-b', help = 'Binning, e.g. "mva_cmb-7 mva_prc-7"')

_RUN2_RAT_PSI2 : Final[float] = 0.62 # Value of rat_psi2 in run2
_RATIO         : Final[PRecRatio] = PRecRatio.psi2 
_BLOCKS : Final[list[str]] = ['4', '3', '2', '1', '5', '6', '7', '8'] 

type NpFltArr = npt.NDArray[numpy.float64]
# ----------------------------------------------------------------------
def _get_block_ratio(project : Project, binning : str) -> tuple[float,float]:
    cfg = CCbarRatioCalculatorConf.load(binning = binning)
    with DataStore.selection(sel = cfg.binning.selection, update = False):
        cal         = CCbarRatioCalculator(
            cfg     = cfg,
            binning = binning,
            project = project)

        ratio = cal.get_ratio(update = False)

    return ratio.get_value(name = _RATIO.variable)
# ----------------------------------------------------------------------
def _get_block_ratios(binning : str, project : Project) -> tuple[NpFltArr, NpFltArr, NpFltArr]:
    vals = []
    errs = []
    for block in _BLOCKS:
        full_binning = f'block-{block} {binning}'
        val, err     = _get_block_ratio(project = project, binning = full_binning)
        vals.append(val)
        errs.append(err)

    return numpy.array(vals), numpy.array(errs), numpy.array(_BLOCKS)
# ----------------------------------------------------------------------
def plot_ratios(binning : str = binning_opt):
    '''
    Run simultaneous fit to resonant modes
    '''
    _, ax = plt.subplots()

    for project in [Project.rk, Project.rkst]:
        vals, errs, blocks = _get_block_ratios(
            binning = binning,
            project = project)

        ax.fill_between(
            blocks,
            vals - errs, # type: ignore
            vals + errs, # type: ignore
            alpha = 0.3,
            color = project.color,
            label = project.latex
        )
        ax.plot(blocks, vals, color = project.color)

    ax.set_ylim(bottom = 0, top = 1)
    ax.set_xlabel('Block')
    ax.set_ylabel(_RATIO.latex)
    ax.axhline(y = _RUN2_RAT_PSI2, color = 'black', linestyle = ':', label = 'Run 2')
    ax.legend()
    plt.show()
# ----------------------------------------------------------------------
