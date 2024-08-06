from hqm2.data_store import data_store

import matplotlib.pyplot as plt
import os

#------------------------------------
def test_simple():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/simple'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
#------------------------------------
def plot_data(arr_dat, plt_dir):
    plt.hist(arr_dat, bins=100, range=[4000, 6000])
    plt.savefig(f'{plt_dir}/data.png')
    plt.close('all')
#------------------------------------
def main():
    test_simple()
#------------------------------------
if __name__ == '__main__':
    main()

