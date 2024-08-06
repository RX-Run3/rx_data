from hqm2.data_store import data_store

import matplotlib.pyplot as plt
import os

#------------------------------------
def plot_data(arr_dat, plt_dir):
    plt.hist(arr_dat, bins=100, range=[4000, 6000])
    plt.savefig(f'{plt_dir}/data.png')
    plt.close('all')
#------------------------------------
def test_simple():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/simple'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
#------------------------------------
def test_cut():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array(cuts={'SB' : 'B_M < 5180'})

    plt_dir = 'tests/data_store/cut'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
#------------------------------------
def main():
    test_simple()
    test_cut()
#------------------------------------
if __name__ == '__main__':
    main()

