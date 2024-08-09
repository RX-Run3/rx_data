import os
import numpy
import matplotlib.pyplot as plt

from log_store import log_store

log=log_store.add_logger('rx_hqm2:wgtc')
#-------------------------------------------------
class wgtc:
    '''
    Class used to calculate weights to correct mass scale and resolution of signal
    '''
    def __init__(self, rdf_dt=None, rdf_mc=None, mrange=None):
        self._rdf_dt = rdf_dt
        self._rdf_mc = rdf_mc

        self._min_cns = 5229
        self._max_cns = 5329

        [self._min_raw, self._max_raw] = mrange 

        self._arr_edge= numpy.linspace(self._min_raw, self._max_raw, 101)

        self._arr_wgt = None
        self._out_dir = None

        self._initialized = False
    #-------------------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._rdf_dt = self._apply_cuts(self._rdf_dt)
        self._rdf_mc = self._apply_cuts(self._rdf_mc)

        self._plot_mass(self._rdf_dt, 'data')
        self._plot_mass(self._rdf_mc,   'mc')

        arr_bc_dt     = self._get_hist(rdf=self._rdf_dt)
        arr_bc_mc     = self._get_hist(rdf=self._rdf_mc)
        self._arr_wgt = numpy.divide(arr_bc_dt, arr_bc_mc, out=numpy.ones_like(arr_bc_dt).astype(float), where=arr_bc_mc != 0)

        self._check_weights()
        self._validate_weights(arr_bc_dt, arr_bc_mc)

        self._initialized = True
    #-------------------------------------------------
    def _apply_cuts(self, rdf):
        cns_mass_cut = f'(B_const_mass_M > {self._min_cns}) && (B_const_mass_M < {self._max_cns})'
        raw_mass_cut = f'(           B_M > {self._min_raw}) && (           B_M < {self._max_raw})'

        rdf = rdf.Filter(cns_mass_cut, 'Constrained')
        rdf = rdf.Filter(raw_mass_cut, 'Raw')

        rep = rdf.Report()
        rep.Print()

        return rdf
    #-------------------------------------------------
    def _plot_mass(self, rdf, kind):
        d_data = rdf.AsNumpy(['B_M', 'B_const_mass_M'])
        for name, arr_mass in d_data.items():
            plt.hist(arr_mass, bins=100, range=[self._min_raw, self._max_raw], histtype='step', label=name)

        plot_path = f'{self._out_dir}/mass_dist_{kind}.png'
        plt.axvline(x=self._min_cns, color='r', linestyle=':')
        plt.axvline(x=self._max_cns, color='r', linestyle=':')
        plt.legend()
        plt.savefig(plot_path)
        plt.close('all')
    #-------------------------------------------------
    def _get_hist(self, rdf=None, weights=None):
        arr_mass     = rdf.AsNumpy(['B_M'])['B_M']
        arr_bc, _, _ = plt.hist(arr_mass, density=True, weights=weights, bins=self._arr_edge) 
        plt.close('all')

        return arr_bc
    #-------------------------------------------------
    def _check_weights(self):
        wgt     = self._arr_wgt
        arr_lrg = wgt[wgt > 2]
        arr_neg = wgt[wgt < 0]

        if arr_lrg.size > 0:
            log.warning(f'Found {arr_lrg.size} weights larger than 2.')

        if arr_neg.size > 0:
            log.warning(f'Found {arr_neg.size} weights smaller than 0.')
    #-------------------------------------------------
    def _validate_weights(self, arr_bc_dt, arr_bc_mc):
        arr_mas_mc = self._rdf_mc.AsNumpy(['B_M'])['B_M']
        arr_mc_wgt = self._calculate_weights(arr_mas_mc)
        arr_bc_co  = self._get_hist(rdf=self._rdf_mc, weights=arr_mc_wgt)
        self._save_mass_dist(dat=arr_bc_dt, sim=arr_bc_mc, cor=arr_bc_co)
    #-------------------------------------------------
    def _calculate_weights(self, arr_mas):
        arr_mc_ind = numpy.digitize(arr_mas, self._arr_edge, right=False)
        arr_mc_ind = arr_mc_ind - 1
        arr_mc_wgt = self._arr_wgt[arr_mc_ind] 

        return arr_mc_wgt
    #-------------------------------------------------
    def _save_mass_dist(self, dat=None, sim=None, cor=None):
        if self._out_dir is None:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

        ax1.stairs(dat, self._arr_edge, label=     'Data')
        ax1.stairs(sim, self._arr_edge, label=       'MC')
        ax1.stairs(cor, self._arr_edge, label='Corrected')

        ax2.stairs(self._arr_wgt, self._arr_edge, color='k')

        plot_path = f'{self._out_dir}/mass_validation_dist.png'
        log.info(f'Saving to: {plot_path}')

        ax1.legend()

        plt.savefig(plot_path)
        plt.close('all')
    #-------------------------------------------------
    @property
    def out_dir(self):
        return self._out_dir

    @out_dir.setter
    def out_dir(self, value):
        os.makedirs(value, exist_ok=True)
        self._out_dir = value
    #-------------------------------------------------
    def get_weights(self, arr_mas=None):
        self._initialize()

        arr_mc_wgt = self._calculate_weights(arr_mas)

        return arr_mc_wgt
#-------------------------------------------------
