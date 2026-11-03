'''
This script makes a summary of MVA scanning toys
'''

import os
import argparse
import seaborn           as sns
import matplotlib.pyplot as plt
import mplhep
from pathlib import Path

import pandas as pnd
from omegaconf             import DictConfig, OmegaConf
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('fitter:summarize_toys')
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    version : str
    cmb_lab = '$MVA_{cmb}$'
    prc_lab = '$MVA_{prc}$'

    mplhep.style.use('LHCb2')
    ana_dir    = Path(os.environ['ANADIR'])
    input_path : Path
    output_path: Path
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Plots summary information from scanning')
    parser.add_argument('-v', '--version' , type=str, help='Version of fits, e.g. v3', required=True)
    args = parser.parse_args()

    Data.version    = args.version
    Data.input_path = Data.ana_dir/f'fits/data/{Data.version}'
    Data.output_path= Data.input_path/'plots'
    Data.output_path.mkdir(exist_ok=True)
# ----------------------
def _load_summary() -> DictConfig:
    '''
    Returns
    -------------
    Dictionary holding contents of `summary.yaml`
    '''
    summary_path = Data.input_path/'summary.yaml'
    if not os.path.isfile(summary_path):
        raise FileNotFoundError(f'Missing: {summary_path}')

    cfg = OmegaConf.load(summary_path)
    if not isinstance(cfg, DictConfig):
        raise ValueError('Loaded summary is not a dictionary')

    return cfg
# ----------------------
def _plot_on_mva_grid(data : DictConfig, name : str, label : str) -> None:
    '''
    Parameters
    -------------
    data : Object holding summary of fit information
    name : Name of the quantity to plot
    label: Latex-like string, used to represent z axis in plots
    '''
    l_cmb = [ toy.wp.cmb for toy in data.values() ]
    l_prc = [ toy.wp.prc for toy in data.values() ]
    l_val = [ toy[name]  for toy in data.values() ]

    plt.figure(figsize=(15, 10))
    df    = pnd.DataFrame({Data.cmb_lab : l_cmb, Data.prc_lab : l_prc, name : l_val})
    heatmap_data = df.pivot(index=Data.cmb_lab, columns=Data.prc_lab, values=name)
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='Spectral', vmin=0, vmax=15)
    plt.gca().invert_yaxis()
    plt.title(label)
    plt.savefig(Data.output_path/f'{name}.png')
    plt.close()
# ----------------------
def _plot_summary(data : DictConfig) -> None:
    '''
    Parameters
    -------------
    data: Dictionary with summary of toy fits
    '''
    _plot_on_mva_grid(data=data, name='median_yld_signal_unc', label=r'$\delta$[%]')
# ----------------------
def main():
    '''
    Entry point
    '''
    _parse_args()

    data = _load_summary()
    _plot_summary(data=data)
# ----------------------
if __name__ == '__main__':
    main()
