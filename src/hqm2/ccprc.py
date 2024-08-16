import os
import zfit
import numpy
import matplotlib.pyplot as plt
import utils_noroot      as utnr
import zutils.utils      as zut

from hqm2.data_store     import data_store
from hqm2.config         import config
from hqm2.pdfmc          import pdfmc 
from hqm2.trfc           import trfc
from hqm2.ratc           import ratc 

from importlib.resources import files
from zutils.plot         import plot      as zfp
from fitter              import zfitter
from log_store           import log_store

log=log_store.add_logger('rx_hqm2:ccprc')
#-----------------------------------
class ccprc:
    '''
    Class used to provide charmonium PDF that leaks to the high-q2 bin. 
    '''
    def __init__(self, obs=None, dset=None, preffix=None, syst=None, brem=None):
        '''
        obs: zfit observable
        dset (str): dataset, representing year, e.g. r1
        preffix (str): String meant to be used for naming of variables
        syst (str): Needed to switch between nominal and alternative models
        brem (int): Needed to check models in brem categories 1 and 2. This component does not exist in brem = 0
        '''
        self._obs   = obs
        self._dset  = dset 
        self._syst  = syst 
        self._brem  = brem
        self._pref  = preffix

        self._qsq_src = 'psi2'
        self._qsq_tgt = 'high'
        self._fft_npt = 1000
        self._bw_mumu = 15
        self._low_sb  = 5180

        self._proc_trf    = 'psi2'
        self._initialized = False
    #---------------------------------
    def _initialize(self):
        if self._initialized:
            return

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
        #TODO: Combinatorial needs to be subtracted
        json_path = files('hqm2_data').joinpath(f'fits/data/{self._dset}_MTOS_{self._qsq_tgt}_lowsb.json')
        json_path = str(json_path)
        if os.path.isfile(json_path):
            log.info(f'Low sideband muon data found, loading')

            l_mass  = utnr.load_json(json_path)
            zdata   = zfit.Data.from_numpy(self._obs, array=numpy.array(l_mass))
            pdf_mmd = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bw_mumu, name='data muon')
        else:
            log.info(f'Low sideband muon data not found, getting it')

            cns_mas_var = {'jpsi' : 'B_const_mass_M', 'psi2' : 'B_const_mass_psi2S_M'}[self._qsq_src]

            obj       = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc='data')
            arr_dat   = obj.get_array(d_cut={'SB' : f'{cns_mas_var} < {self._low_sb}'})
            l_mass    = arr_dat.tolist()
            utnr.dump_json(l_mass, json_path)

            zdata     = zfit.Data.from_numpy(self._obs, array=arr_dat)
            pdf_mmd   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bw_mumu, name='data muon')

            obj=zfp(data=arr_dat, model=pdf_mmd, result=None)
            obj.plot(plot_range=[4200, 6000])

            plot_path = json_path.replace('.json', '.png')
            plot_dir  = os.path.dirname(plot_path)
            os.makedirs(plot_dir, exist_ok=True)
            plt.savefig(plot_path)
            plt.close('all')

        return pdf_mmd
    #---------------------------------
    def _get_ratio(self):
        cal        = ratc(obs=self._obs, dset=self._dset)
        [val, err] = cal.get_ratio()
        par        = zfit.param.Parameter(f'r_psi2_{self._dset}', val, 0, 1)

        return par 
    #---------------------------------
    def _get_trf(self):
        obj     = trfc(
                obs    = self._obs, 
                dset   = self._dset, 
                pref   = self._pref,
                proc   = self._proc_trf, 
                qsq_src= self._qsq_src, 
                qsq_tgt= self._qsq_tgt, 
                ) 

        pdf_trf = obj.get_trf()

        return pdf_trf
    #---------------------------------
    def get_pdf(self):
        self._initialize()

        pdf_mmd = self._get_muon_pdf()
        pdf_trf = self._get_trf()
        pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_mmd, kernel=pdf_trf, name='PRec', n=self._fft_npt)

        obj     = pdfmc(obs=self._obs, dset=self._dset, proc='psi2', qsq='high')
        pdf_res = obj.get_pdf()

        r       = self._get_ratio()
        pdf     = zfit.pdf.SumPDF([pdf_prc, pdf_res], r)

        return pdf
#-----------------------------------

