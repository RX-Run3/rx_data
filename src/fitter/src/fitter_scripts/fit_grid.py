'''
This script will make plots of variables in a grid representing fits
for different MVA scores
'''

import os
import re
import glob
import math
import argparse

import mplhep
import seaborn           as sns
import matplotlib.pyplot as plt
import pandas            as pnd

from dmu.logging.log_store import LogStore
from dmu.generic           import utilities as gut

log=LogStore.add_logger('rx_fitter:fit_grid')
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    q2bin   = ''
    ana_dir = os.environ['ANADIR']
    out_dir = f'{ana_dir}/mva/optimization/wp'
    d_data  = {'mva_cmb' : [], 'mva_prc' : [], 'nbkg' : [], 'sign' : [], 'sosqsb' : []}
    regex   = r'.*\/(\d{3})_(\d{3})\/.*'
    sig_yld = 'yld_signal'
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='This script is used to plot fitting parameters in a grid')
    parser.add_argument('-q', '--q2bin' , type=str, help='q2bin, e.g. central', required=True)
    args   = parser.parse_args()

    Data.q2bin = args.q2bin
# ----------------------
def _read_values(path : str) -> tuple[float,float,float]:
    '''
    Parameters
    -------------
    path: Path to YAML file with fitting parameters

    Returns
    -------------
    Tuple with:
        - Background yield
        - Significance, defined as errorN/N
        - S/sqrt(S+B)
    '''
    data = gut.load_json(path=path)

    significance = -1
    nbkg         =  0
    nsig         =  0
    for name, d_pars in data.items():
        if not name.startswith('n'):
            continue

        if name == Data.sig_yld:
            nsig : float = d_pars['value']
            esig : float = d_pars['error']

            significance = 100 * esig / nsig
            continue

        log.debug(f'Using background {name}')

        nbkg += d_pars['value']

    sosqsb = nsig / math.sqrt(nsig + nbkg)

    return nbkg, significance, sosqsb
# ----------------------
def _fill_data(path : str) -> None:
    '''
    Parameters
    -------------
    path : Path to YAML file with fitting parameters
    '''
    mtch = re.match(Data.regex, path)
    if not mtch:
        raise ValueError(f'Cannot match {Data.regex} with {path}')

    str_mva_cmb, str_mva_prc = mtch.groups()

    mva_cmb = float(str_mva_cmb) / 100.
    mva_prc = float(str_mva_prc) / 100.

    nbkg, sign, sosqsb = _read_values(path=path)

    Data.d_data['mva_cmb'].append(mva_cmb)
    Data.d_data['mva_prc'].append(mva_prc)
    Data.d_data['nbkg'   ].append(nbkg   )
    Data.d_data['sign'   ].append(sign   )
    Data.d_data['sosqsb' ].append(sosqsb )
# ----------------------
def _load_data() -> pnd.DataFrame:
    '''
    Returns
    -------------
    Pandas dataframe with MVA coordinates and quantity to plot
    '''
    path_wc = f'{Data.ana_dir}/fits/data/*/rare/electron/data/DATA_24_p/Hlt2RD_BuToKpEE_MVA_rx_{Data.q2bin}/parameters.yaml'
    l_path  = glob.glob(path_wc)
    if len(l_path) == 0:
        raise ValueError('No files found in: {path_wc}')

    for path in l_path:
        _fill_data(path=path)

    df = pnd.DataFrame(Data.d_data)

    return df
# ----------------------
def _initialize() -> None:
    '''
    This function should initialize style, loggers, etc
    '''
    mplhep.style.use('LHCb2')
    os.makedirs(Data.out_dir, exist_ok=True)
# ----------------------
def _plot_data(df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    df: DataFrame with MVA working points and fitting quanities

    Returns
    -------------
    This method is in charge of making plots
    '''
    _plot_variable(df=df, variable=  'sign')
    _plot_variable(df=df, variable='sosqsb')
# ----------------------
def _plot_variable(df : pnd.DataFrame, variable : str) -> None:
    '''
    Parameters
    -------------
    df: DataFrame with data
    variable: Name of variable for Z axis
    '''
    pivot = df.pivot_table(index='mva_prc', columns='mva_cmb', values=variable)
    pivot = pivot.sort_index(ascending=False)
    pivot = pivot.sort_index(axis=1)

    max_sig = {'sign' : 20, 'sosqsb' : None}[variable]

    plt.figure(num=variable, figsize=(15, 10))
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='viridis', vmin=0, vmax=max_sig)
    plt.title('Significance vs MVA WP')
    plt.xlabel(r'$MVA_{cmb}$')
    plt.ylabel(r'$MVA_{prc}$')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'{Data.out_dir}/{variable}_{Data.q2bin}.png')
    plt.close(variable)
# ----------------------
def main():
    '''
    Entry point
    '''
    _parse_args()
    _initialize()
    df = _load_data()
    _plot_data(df=df)
# ----------------------
if __name__ == '__main__':
    main()
