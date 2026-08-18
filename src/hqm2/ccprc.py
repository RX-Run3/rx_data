import os
import zfit
import math
import numpy
import jacobi            as jac
import matplotlib.pyplot as plt
import utils_noroot      as utnr
import zutils.utils      as zut

from hqm2.data_store     import data_store
from hqm2.config         import config
from hqm2.pdfmc          import pdfmc
from hqm2.trfc           import TransferFunction
from hqm2.ratc           import ratc

from importlib.resources import files
from zutils.plot         import plot      as zfp
from fitter              import zfitter
from log_store           import log_store
from jacobi              import propagate

log=log_store.add_logger('rx_hqm2:ccprc')
#-----------------------------------
class ccprc:
    '''
    Class used to provide charmonium PDF that leaks to the high-q2 bin.
    '''
    def __init__(
            self,
            obs    =None,
            dset   =None,
            syst   =None,
            brem   =None,
            preffix=None,
            qsq_src='psi2',
            ):
        '''
        obs          : zfit observable
        dset    (str): dataset, representing year, e.g. r1
        syst    (str): Needed to switch between nominal and alternative models
        brem    (int): Needed to check models in brem categories 1 and 2. This component does not exist in brem = 0
        preffix (str): String meant to be used for naming of variables
        qsq_src (str): Source q2 bin, either psi2S (default) or jpsi, needed to pick up muon data sample and transfer function
        '''
        self._obs   = obs
        self._dset  = dset
        self._syst  = syst
        self._brem  = brem
        self._pref  = preffix

        self._qsq_src = qsq_src

        self._proc    = None
        self._qsq_tgt = 'high'
        self._fft_npt = 1000
        self._bw_mumu = 15
        self._low_sb  = 5180

        self._initialized = False
    #---------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._proc = {'psi2' : 'psi2', 'jpsi' : 'ctrl'}[self._qsq_src]

        self._check_brem()

        self._initialized = True
    #---------------------------------
    def _check_brem(self):
        if self._brem not in [None, 1, 2]:
            log.error(f'Invalid brem category: {self._brem}')
            raise

        if self._brem is None:
            config.binning = dict()
            return

        config.binning['var'] =                'cbrem'
        config.binning['bin'] =             self._brem
        config.binning['cut'] = f'cbrem=={self._brem}'
    #---------------------------------
    def _get_muon_pdf(self):
        arr_mass  = self._get_muon_sb()
        zdata     = zfit.Data.from_numpy(self._obs, array=arr_mass)
        pdf_mmd   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bw_mumu, name='data muon')
        pdf_mmd.arr_mass = arr_mass

        return pdf_mmd
    #---------------------------------
    def _plot_fit(self, pdf_mm, pdf_ee):
        plt_rng = [4200, 6000]
        nbins   = 100

        obj=zfp(data=pdf_mm.arr_mass, model=pdf_mm, result=None)
        obj.plot(plot_range=plt_rng, nbins=nbins, d_leg={'data muon' : 'Original muon', 'Data' : 'Low SB data'})
        nentries = pdf_mm.arr_mass.size
        info = f'Entries:{nentries}; Bandwidth: {self._bw_mumu}'

        ax   = obj.axs[0]
        self._plot_pdf(pdf_ee, nbins=nbins, ax=ax, norm=nentries, rng=plt_rng)

        ax.set_title(info)
        ax.legend()

        plot_path = config.make_data_path(kind='fits', dset=self._dset, dname=f'data_MTOS_{self._qsq_src}', fname='fit.png')
        plt.savefig(plot_path)
        plt.close()
    #---------------------------------
    def _plot_pdf(self, pdf, nbins=None, ax=None, norm=None, rng=None):
        arr_x = numpy.linspace(rng[0], rng[1], nbins)
        arr_y = pdf.pdf(arr_x)
        scale = norm / numpy.sum(arr_y)
        arr_y = scale * arr_y

        ax.plot(arr_x, arr_y, color='r', label='Smeared')
    #---------------------------------
    def _get_muon_sb(self):
        cns_mas_var = {'jpsi' : 'B_const_mass_M', 'psi2' : 'B_const_mass_psi2S_M'}[self._qsq_src]

        #TODO: Combinatorial needs to be subtracted
        obj       = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc='data')
        arr_dat   = obj.get_array(d_cut={'SB' : f'{cns_mas_var} < {self._low_sb}'})

        return arr_dat
    #---------------------------------
    def _transform_ratio(self, val, err):
        tval, tvar = propagate(lambda x : 1. / (1. + 1./x), val, err**2)
        terr       = math.sqrt(tvar)

        log.debug(60 * '-')
        log.debug('Transforming ratio')
        log.debug(60 * '-')
        log.debug(f'{val:<20.3f}{"-->":20}{tval:<20.3f}')
        log.debug(f'{err:<20.3f}{"-->":20}{terr:<20.3f}')

        return tval, terr
    #---------------------------------
    def _get_ratio_value(self):
        '''
        Returns numerical value and error of ratio of prec and fully reco
        '''
        if self._dset != 'comb':
            cal        = ratc(obs=self._obs, dset=self._dset, proc=self._proc)
            [val, err] = cal.get_ratio()

            return val, err

        log.warning(f'Combined dataset ratio requested, using weigheted average instead of fit to full dataset')
        log.debug(40 * '-')
        log.debug(f'{"Value":<20}{"Error":<20}')
        log.debug(40 * '-')

        l_val = []
        l_var = []
        for dset in ['r1', 'r2p1', '2017', '2018']:
            cal        = ratc(obs=self._obs, dset=dset, proc=self._proc)
            [val, err] = cal.get_ratio()
            log.debug(f'{val:<20.3f}{err:<20.3f}')
            l_val.append(val)
            l_var.append(err ** 2)

        cov      = numpy.diag(l_var)
        val, var = jac.propagate(lambda x : sum(x)/len(x), l_val, cov)
        err      = math.sqrt(var)
        log.debug(40 * '-')
        log.debug(f'Average: {val:<20.3f}{err:<20.3f}')
        log.debug(40 * '-')

        return val, err
    #---------------------------------
    def _get_ratio(self):
        '''
        Returns zfit parameter representing the ratio and a dictionary with the constrain
        '''
        val, err   = self._get_ratio_value()
        tval, terr = self._transform_ratio(val, err)
        name       = f'r_{self._proc}_{self._dset}' if self._brem is None else f'r_{self._proc}_{self._dset}_brem_{self._brem}'
        label      = f'Ratio: {val:.3f}; Fraction: {tval:.3f}'
        par        = zfit.param.Parameter(name, tval, 0, 1, label=label)
        d_cns      = {name : [tval, terr]}

        return par, d_cns
    #---------------------------------
    def _get_trf(self):
        obj     = TransferFunction(
                obs    = self._obs,
                trigger   = self._dset,
                prefix   = self._pref,
                sample   = self._proc,
                source= self._qsq_src,
                target= self._qsq_tgt,
                )

        pdf_trf = obj.get_trf()

        return pdf_trf
    #---------------------------------
    def _get_pdf_name(self):
        name = f'{self._pref}_{self._syst}_{self._dset}'
        if self._brem is None:
            return name

        return f'{name}_brem_{self._brem}'
    #---------------------------------
    def get_pdf(self, plot_pdf=False):
        self._initialize()

        pdf_mmd = self._get_muon_pdf()
        pdf_trf = self._get_trf()

        try:
            pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_mmd, kernel=pdf_trf, name='PRec', n=self._fft_npt)
        except:
            log.error(f'Cannot build convolution for:')
            log.info(f'{"Dataset":<15}{self._dset:<20}')
            log.info(f'{"Systematic":<15}{self._syst:<20}')
            log.info(f'{"Brem cat":<15}{str(self._brem):<20}')
            log.info(f'{"Preffix":<15}{self._pref:<20}')
            raise

        if plot_pdf:
            self._plot_fit(pdf_mmd, pdf_prc)

        obj     = pdfmc(obs=self._obs, dset=self._dset, proc=self._proc, qsq='high')
        pdf_res = obj.get_pdf()

        r, d_cns = self._get_ratio()
        name     = self._get_pdf_name()
        pdf      = zfit.pdf.SumPDF([pdf_prc, pdf_res], r, name=name)
        pdf.d_cns= d_cns

        config.binning = dict()

        return pdf
#-----------------------------------

