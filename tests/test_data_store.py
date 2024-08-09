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
def test_vec():
    obj_jps = data_store(qsq='jpsi', dset='2018', trig='MTOS', proc='data')
    arr_jps = obj_jps.get_array(variable='B_const_mass_M')

    obj_psi = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_psi = obj_psi.get_array(variable='B_const_mass_psi2S_M')

    plt_dir = 'tests/data_store/vec'
    os.makedirs(plt_dir, exist_ok=True)

    plt.hist(arr_jps, bins=100, range=[3500, 5500], histtype='step', density=True, label='ctrl')
    plt.hist(arr_psi, bins=100, range=[3500, 5500], histtype='step', density=True, label='psi2')
    plt.legend()
    plt.savefig(f'{plt_dir}/data.png')
    plt.close('all')
#------------------------------------
def test_cut():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array(d_cut={'SB' : 'B_M < 5180'})

    plt_dir = 'tests/data_store/cut'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
#------------------------------------
def test_dset():
    obj     = data_store(qsq='psi2', dset='r1', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/dset'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
#------------------------------------
def main():
    test_vec()
    test_simple()
    test_dset()
    test_cut()
#------------------------------------
if __name__ == '__main__':
    main()

