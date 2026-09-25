'''
Module used to run fits to resonant mode data
'''
import os
import typer
import numpy
import numpy.typing as npt
import matplotlib.pyplot as plt

from pathlib        import Path
from typing         import Final
from dmu            import LogStore
from hqm.types      import Mode
from hqm.config     import CCbarRatioCalculatorConf
from hqm.data_store import DataStore
from hqm.ratc       import CCbarRatioCalculator
from hqm.types      import PRecRatio
from rx_common      import Project

binning_opt = typer.Option(...  , '-b', help = 'Binning, e.g. "mva_cmb-7 mva_prc-7"')

_ANADIR   : Final[Path ]                 = Path(os.environ['ANADIR'])
_RUN2_RAT : Final[dict[PRecRatio,float]] = { PRecRatio.psi2 : 0.62, PRecRatio.jpsi : 0.7 } # Value of ratios in run2
_BLOCKS   : Final[list[str]]             = ['4', '3', '2', '1', '5', '6', '7', '8']
_PROJECTS : Final[list[Project]]         = [Project.rk]

log=LogStore.add_logger('hqm:plot_ratios')

type NpFltArr = npt.NDArray[numpy.float64]
# ----------------------------------------------------------------------
def _get_block_ratio(
    kind    : PRecRatio,
    project : Project,
    binning : str) -> tuple[float,float]:
    cfg = CCbarRatioCalculatorConf.load(binning = binning)
    with DataStore.selection(sel = cfg.binning.selection, update = False):
        cal         = CCbarRatioCalculator(
            cfg     = cfg,
            binning = binning,
            project = project)

        ratio = cal.get_ratio(mode = Mode.read)

    return ratio.get_value(name = kind.variable)
# ----------------------------------------------------------------------
def _get_block_ratios(
    kind    : PRecRatio,
    binning : str,
    project : Project) -> tuple[NpFltArr, NpFltArr, NpFltArr]:
    vals = []
    errs = []
    for block in _BLOCKS:
        full_binning = f'block-{block} {binning}'
        val, err     = _get_block_ratio(project = project, binning = full_binning, kind = kind)
        vals.append(val)
        errs.append(err)

    return numpy.array(vals), numpy.array(errs), numpy.array(_BLOCKS)
# ----------------------------------------------------------------------
def _plot_ratio(
    binning : str,
    kind    : PRecRatio):
    '''
    Run simultaneous fit to resonant modes
    '''
    _, ax = plt.subplots()

    for project in _PROJECTS:
        vals, errs, blocks = _get_block_ratios(
            kind    = kind,
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

    ax.set_ylim(bottom = 0, top = 2.0)
    ax.set_xlabel('Block')
    ax.set_ylabel(kind.latex)
    ax.axhline(y = _RUN2_RAT[kind], color = 'black', linestyle = ':', label = 'Run 2')
    ax.legend()

    var = kind.variable

    name_binning = binning.replace(' ', '_')
    out_path= _ANADIR / 'DB/hqm/ccbar_pdf/latest/plots' / f'{var}_{name_binning}.png'
    out_path.parent.mkdir(exist_ok = True, parents = True)

    log.info(f'Saving to: {out_path}')

    plt.savefig(out_path)
    plt.close()
# ----------------------------------------------------------------------
def plot_ratios(binning : str = binning_opt) -> None:
    for kind in PRecRatio:
        _plot_ratio(binning = binning, kind = kind)
# ----------------------------------------------------------------------
