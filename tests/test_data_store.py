from hqm2.data_store import data_store
from hqm2.config     import Conf 
from log_store       import log_store

import matplotlib.pyplot as plt
import os
import mplhep

# ------------------------------------
def plot_data(arr_dat, plt_dir, name='data'):
    plt.hist(arr_dat, bins=100)
    plt.savefig(f'{plt_dir}/{name}.png')
    plt.close('all')
# ------------------------------------
def set_logs():
    log_store.set_level('rx_hqm2:data_store'      , 10)
    log_store.set_level('rx_scripts:storage/cache', 10)

    log_store.set_level('rx_hqm2:ccprc'           , 10)
    log_store.set_level('rx_hqm2:ratc'            , 30)
    log_store.set_level('scripts:zutils/utils'    , 20)
    log_store.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    log_store.set_level('tools:calc_utility'      , 40)
# ------------------------------------
def test_rdf():
    obj= data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    obj.get_rdf(variables=['B_M', 'B_const_mass_M'])
# ------------------------------------
def test_simple():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/simple'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
# ------------------------------------
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
# ------------------------------------
def test_cut():
    obj     = data_store(qsq='psi2', dset='2018', trig='MTOS', proc='data')
    arr_dat = obj.get_array(d_cut={'SB' : 'B_M < 5180'})

    plt_dir = 'tests/data_store/cut'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
# ------------------------------------
def test_dset():
    obj     = data_store(qsq='psi2', dset='r1', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/dset'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
# ------------------------------------
def test_binning():
    Conf.binning['var'] =        'B_PT'
    Conf.binning['bin'] =           '1'
    Conf.binning['cut'] = 'B_PT < 5750'

    obj     = data_store(qsq='psi2', dset='r1', trig='MTOS', proc='data')
    arr_dat = obj.get_array()

    plt_dir = 'tests/data_store/binninng'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir)
# ------------------------------------
def test_rare(proc):
    obj     = data_store(qsq='high', dset='2018', trig='ETOS', proc=proc)
    arr_dat = obj.get_array(variable='B_ETA')

    plt_dir = 'tests/data_store/rare'
    os.makedirs(plt_dir, exist_ok=True)

    plot_data(arr_dat, plt_dir, name=proc)
# ------------------------------------
def main():
    plt.style.use(mplhep.style.LHCb2)
    set_logs()

    test_rare('sign')
    return
    test_rare('bpks')
    test_rare('bdks')
    test_rare('bsph')

    test_binning()
    test_rdf()
    test_vec()
    test_simple()
    test_dset()
    test_cut()
# ------------------------------------
if __name__ == '__main__':
    main()
