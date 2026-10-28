'''
Script used to compare performance of classifiers
'''
import os
import argparse
import yaml
import mplhep
import matplotlib.pyplot as plt
import pandas            as pnd

from sklearn.metrics import auc
from dmu             import LogStore

plt.style.use(mplhep.style.LHCb2)
log=LogStore.add_logger('dmu:ml:compare_classifiers')
# ------------------------------
class Data:
    '''
    Data class
    '''
    out_path : str
    cfg_path : str
    logl     : int
    cfg      : dict
# ------------------------------
def _initialize() -> None:
    log.info(f'Loading settings from: {Data.cfg_path}')
    with open(Data.cfg_path, encoding='utf-8') as ifile:
        Data.cfg = yaml.safe_load(ifile)

    Data.out_path = Data.cfg['out_dir']
    os.makedirs(Data.out_path, exist_ok=True)
# ------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description='Used to perform comparisons of classifier performances')
    parser.add_argument('-c', '--conf' , help='Path to configuration path', required=True)
    parser.add_argument('-l', '--logl' , help='Logging level', choices=[10, 20, 30], default=20)
    args = parser.parse_args()

    Data.cfg_path = args.conf
    Data.logl     = args.logl
# ------------------------------
def _plot_roc(name : str, path : str) -> None:
    roc_path = f'{path}/fold_all/roc.json'
    df = pnd.read_json(roc_path)

    plt.figure(num='ROC')
    xval = df['x'].to_numpy()
    yval = df['y'].to_numpy()
    area = auc(xval, yval)

    plt.plot(xval, yval, label=f'{name}: {area:.3f}')
# ------------------------------
def _compare():
    for name, cls_path in Data.cfg['classifiers'].items():
        _plot_roc(name=name, path=cls_path)

    _save_roc()
# ------------------------------
def _save_roc():
    d_set = Data.cfg['roc']
    if 'xrange' in d_set:
        plt.xlim(d_set['xrange'])

    if 'yrange' in d_set:
        plt.ylim(d_set['yrange'])

    plt.figure(num='ROC')
    plt.legend()
    plt.grid()
    plt.xlabel('Signal Efficiency')
    plt.ylabel('Background Rejection')
    plt.savefig(f'{Data.out_path}/roc.png')
# ------------------------------
def main():
    '''
    Start here
    '''
    _parse_args()
    _initialize()
    _compare()
# ------------------------------
if __name__ == '__main__':
    main()
