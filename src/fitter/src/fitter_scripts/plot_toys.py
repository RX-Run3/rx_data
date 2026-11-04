'''
Script used to plot distributions from toy fits
by loading pandas dataframes stored as parquet files
'''
import os
import re
import copy
import argparse
import mplhep
import pandas as pnd

from pathlib                 import Path
from omegaconf               import DictConfig, OmegaConf
from tqdm.contrib.concurrent import process_map
from dmu.generic             import utilities as gut
from dmu.logging.log_store   import LogStore
from fitter.toy_plotter      import ToyPlotter

log=LogStore.add_logger('fitter:plot_toys')
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    nworkers   : int
    log_lvl    : int
    version    : str
    identifier : str
    dry_run    : bool
    cfg        : DictConfig
    FILENAME   = 'toys.parquet'
# ----------------------
def _set_logs() -> None:
    '''
    This method will set the log level of this
    and other tools
    '''
    LogStore.set_level('fitter:plot_toys', Data.log_lvl)

    if log.getEffectiveLevel() < 20:
        LogStore.set_level('fitter:toy_plotter', Data.log_lvl)
    else:
        LogStore.set_level('fitter:toy_plotter'  , 30)
        LogStore.set_level('dmu:plotting:Plotter', 30)
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to make plots from outputs of toy fits')
    parser.add_argument('-v', '--version'    , type=str, help='Version of toy fits, e.g. v2', required=True)
    parser.add_argument('-i', '--identifier' , type=str, help='Identifier of toy, if not passed, will do all toys')
    parser.add_argument('-l', '--log_level'  , type=int, help='Log level', default=20)
    parser.add_argument('-n', '--nworkers'   , type=int, help='Number of workers, to process in parallel', default=1)
    parser.add_argument('-d', '--dry_run'    , help='If used, will skip plotting step', action='store_true')
    args = parser.parse_args()

    Data.version    = args.version
    Data.identifier = args.identifier
    Data.log_lvl    = args.log_level
    Data.dry_run    = args.dry_run
    Data.nworkers   = args.nworkers
# ----------------------
def _get_paths(source_path : Path) -> list[Path]:
    '''
    Parameters
    -------------
    source_path: Path where the search for FNAME files are searched Returns
    -------------
    List of paths to parquet files with dataframes
    '''
    log.debug(f'Looking for files in: {source_path}')
    l_path = source_path.rglob(Data.FILENAME)
    l_path = list(l_path)
    l_path.sort()
    npath = len(l_path)
    if npath == 0:
        raise ValueError(f'No paths to {Data.FILENAME} found in {source_path}')

    if isinstance(Data.identifier, str):
        l_path = [ path for path in l_path if Data.identifier in str(path) ]
        npath  = len(l_path)
        if npath == 0:
            raise ValueError(f'No paths to {Data.FILENAME} found in {source_path} and with substring {Data.identifier}')

    log.info(f'Found {npath} paths')

    return l_path
# ----------------------
def _run(input_path : Path) -> DictConfig:
    '''
    Parameters
    -------------
    input_path: Path to parquet file
    '''
    cfg = copy.deepcopy(Data.cfg)
    cfg.saving.plt_dir = input_path.parent/'plots'

    df  = pnd.read_parquet(input_path)
    ptr = ToyPlotter(df=df, cfg=cfg)
    cfg = ptr.plot()
    cfg = _attach_wp(cfg=cfg, path=input_path)

    return cfg
# ----------------------
def _save_summary(out_dir : Path, l_cfg : list[DictConfig]) -> None:
    '''
    This function will save a summary of the fits for all working
    poings in a YAML file

    Parameters
    -------------
    out_dir: Output directory
    l_cfg  : List of config dictionaries, one per toy
    '''
    out_path = out_dir/'summary.yaml'

    log.info(f'Saving summary to: {out_path}')

    d_cfg = { itoy : cfg for itoy, cfg in enumerate(l_cfg) }
    cfg   = OmegaConf.create(obj=d_cfg)

    OmegaConf.save(config=cfg, f=out_path)
# ----------------------
def _attach_wp(cfg : DictConfig, path : Path) -> DictConfig:
    '''
    Parameters
    -------------
    cfg : Config with summary of toy fit
    path: Path to directory with outputs of fit

    Returns
    -------------
    Updated config with working point attached
    '''
    mtch = re.search(r'(\d{3})_(\d{3})', str(path))
    if not mtch:
        raise ValueError(f'Cannot extract MVA WP substring from: {path}')

    [cmb, prc] = mtch.groups()

    cmb = float(cmb) / 100.
    prc = float(prc) / 100.

    cfg['wp'] = {'cmb' : cmb, 'prc' : prc}

    return cfg
# ----------------------
def main():
    '''
    Entry point
    '''
    _parse_args()
    _set_logs()
    mplhep.style.use('LHCb2')

    Data.cfg = gut.load_conf(package='fitter_data', fpath='toys/plotter.yaml')
    root_dir = Path(os.environ['ANADIR'])
    inpt_dir = root_dir/'fits/data'/Data.version
    l_path   = _get_paths(source_path=inpt_dir)

    log.info('Plotting:')

    if Data.dry_run:
        return

    l_cfg = process_map(_run, l_path, max_workers=Data.nworkers, ascii=' -')

    _save_summary(out_dir=inpt_dir, l_cfg=l_cfg)
# ----------------------
if __name__ == '__main__':
    main()
