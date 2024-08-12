from hqm2.data_store     import data_store
from hqm2.pdfmc          import pdfmc
from hqm2.trfc           import trfc

from zutils.plot         import plot      as zfp
from importlib.resources import files
from log_store           import log_store

import os
import zfit
import numpy
import utils_noroot as utnr
import zutils.utils as zut
import matplotlib.pyplot as plt

log=log_store.add_logger('rx_hqm2:ratc')
#-----------------------------
class ratc:
    def __init__(self, obs=None, dset=None):
        self._dset = dset
        self._obs  = obs

        self._plot_range = [4000, 6000]
        self._bandwidth  = 15
        self._fft_npt    = 1000
        self._sb_mass    = 5180
        self._d_pdf_dat  = dict() 
        self._out_dir    = None

        self._rat_psi2 = zfit.param.Parameter('rat_psi2', 0.1, 0, 1)
        self._rat_ctrl = zfit.param.Parameter('rat_ctrl', 0.1, 0, 1)

        #npr_xy Yiels of sample x in bin y, p=psi2, c=ctrl
        self._npr_cc= zfit.param.Parameter('npr_cc', 1e3, 0, 4e4)
        self._npr_cp= zfit.param.Parameter('npr_cp', 1e3, 0, 4e4)
        self._npr_pc= zfit.param.Parameter('npr_pc', 1e3, 0, 4e4)
        self._npr_pp= zfit.param.Parameter('npr_pp', 1e3, 0, 4e4)

        self._initialized=False
    #-----------------------------
    def _initialize(self):
        if self._initialized:
            return

        out_dir       = files('hqm2_data').joinpath(f'ratios/{self._dset}')
        self._out_dir = str(out_dir)

        os.makedirs(self._out_dir, exist_ok=True)

        self._initialized=True
    #-----------------------------
    def get_ratio(self):
        self._initialize()

        json_path = f'{self._out_dir}/parameters.json'
        if os.path.isfile(json_path):
            log.info(f'Parameters file found: {json_path}')
            d_par = utnr.load_json(json_path)

            return d_par['rat_psi2']

        log.info('Parameters file not found, recalculating ratio')

        rat = self._get_ratio(json_path)

        return rat
    #-----------------------------
    def _get_ratio(self, json_path):
        nll_psi2= self._get_nll('psi2')
        nll_ctrl= self._get_nll('ctrl')

        nll     = nll_psi2 + nll_ctrl
        res     = self._sim_fit(nll)

        log.info('Plotting')
        self._plot_fit('psi2')
        self._plot_fit('ctrl')

        self._save_figs()
        return

        log.info('Saving parameters')
        d_par = zut.fit_result_to_dict(res)
        utnr.dump_json(d_par, json_path)

        return d_par['rat_psi2']
    #-----------------------------
    def _get_nll(self, proc):
        qsq     = {'ctrl' : 'jpsi', 'psi2' : 'psi2'}[proc]

        pdf     = self._get_model(qsq=qsq)
        ds      = data_store(qsq=qsq, dset=self._dset, trig='ETOS', proc='data')
        arr_dat = ds.get_array()
        zdat    = zfit.Data.from_numpy(obs=self._obs, array=arr_dat)
        nll     = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=zdat)

        self._d_pdf_dat[proc] = arr_dat, pdf

        return nll
    #-----------------------------
    def _get_model(self, qsq=None):
        '''
        qsq (str): Want to model in this q2 bin
        '''
        pdf_prps = self._get_pr_pdf(proc='psi2', qsq=qsq)
        pdf_prjp = self._get_pr_pdf(proc='ctrl', qsq=qsq)

        pdf_psi2 = self._get_mc_pdf(proc='psi2', qsq=qsq) 
        pdf_ctrl = self._get_mc_pdf(proc='ctrl', qsq=qsq) 

        pdf = zfit.pdf.SumPDF([
                    pdf_prps,
                    pdf_prjp, 
                    pdf_psi2,
                    pdf_ctrl, 
                    ])

        return pdf
    #-----------------------------
    @utnr.timeit
    def _sim_fit(self, nll):
        log.info('Fitting')
        minimizer = zfit.minimize.Minuit()
        res       = minimizer.minimize(nll)
        res.hesse(method='minuit_hesse')

        print(res)

        return res
    #-----------------------------
    def _get_mc_pdf(self, proc=None, qsq=None):
        obj = pdfmc(obs=self._obs, dset=self._dset, proc=proc, qsq=qsq)
        pdf = obj.get_pdf()

        rat = {'ctrl' : self._rat_ctrl, 'psi2' : self._rat_psi2}[proc]
        npr = self._get_pr_yield(proc=proc, qsq=qsq) 
        nfr = zfit.ComposedParameter(f'nfr_{proc}_{qsq}', func=lambda d_par : d_par['p1'] / d_par['p2'], params={'p1' : npr, 'p2' : rat} )

        pdf = pdf.create_extended(nfr, name= self._get_pdf_name(proc=proc, kind='fr'))

        return pdf
    #-----------------------------
    def _get_pdf_name(self, proc=None, kind=None):
        d_fr_name = {
                'psi2' : r'$B^+\to \psi(2S)(\to e^+e^-) K^+$',
                'ctrl' : r'$B^+\to J/\psi(\to e^+e^-) K^+$',
                }
        d_pr_name = { 
                'psi2' : r'$B^+\to \psi(2S)(\to e^+e^-) X$',
                'ctrl' : r'$B^+\to J/\psi(\to e^+e^-) X$',
                }

        d_name = {
                'fr' : d_fr_name,
                'pr' : d_pr_name,
                }

        return d_name[kind][proc]
    #-----------------------------
    def _get_pr_pdf(self, proc=None, qsq=None):
        '''
        proc(str): Component that has to be modelled, provides muon MC sample and source q2 bin for transfer function.
        qsq (str): q2 bin where PDF lives, target q2.
        '''

        mas_cns   = {'psi2' : 'B_const_mass_psi2S_M', 'ctrl' : 'B_const_mass_M'}[proc]
        qsq_src   = {'psi2' :                 'psi2', 'ctrl' :           'jpsi'}[proc]

        obj       = trfc(obs=self._obs, qsq_src=qsq_src, qsq_tgt=qsq, proc=proc, dset=self._dset, pref=f'{qsq_src}_{qsq}_pr')
        pdf_trf   = obj.get_trf()

        obj       = data_store(qsq=qsq_src, dset=self._dset, trig='MTOS', proc='data')
        arr_dt_mm = obj.get_array(variable='B_M', d_cut={'sb_mass' : f'{mas_cns} < {self._sb_mass}'})
        #arr_dt_mm = self._extend_distribution(arr_tot=arr_dt_mm, qsq_src=qsq_src)

        self._book_histogram(name=f'mm_{qsq}', label=qsq_src, binning=numpy.linspace(3500, 5300, 100), arr_val=arr_dt_mm)

        zdata     = zfit.Data.from_numpy(self._obs, array=arr_dt_mm)
        pdf_mm    = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bandwidth, name='PRec')
        pdf_ee    = zfit.pdf.FFTConvPDFV1(func=pdf_mm, kernel=pdf_trf, name=self._get_pdf_name(proc=proc, kind='pr') , n=self._fft_npt)
        nevt      = self._get_pr_yield(proc=proc, qsq=qsq)

        self._book_pdf(name=f'pdf_{proc}_{qsq}', pdf=pdf_mm, label='Muon'   , minx=3500, maxx=6000)
        self._book_pdf(name=f'pdf_{proc}_{qsq}', pdf=pdf_ee, label='Smeared', minx=3500, maxx=6000)
        plt.title(f'Source $q^2$: {qsq_src}; Target $q^2$: {qsq}')

        pdf_ee.set_yield(nevt)

        return pdf_ee
    #-----------------------------
    def _extend_distribution(self, arr_tot=None, qsq_src=None):
        if qsq_src != 'jpsi':
            return arr_tot

        arr_val       = arr_tot[arr_tot < 4450]
        shift         = 450
        binning       = numpy.linspace(3550, 4000, 101)

        arr_shf       = arr_val - shift 
        l_bc, l_ed    = numpy.histogram(arr_shf, bins=binning)
        l_bc          = l_bc - (l_bc[-1] - l_bc[0])
        nentries      = numpy.sum(l_bc)
        nentries      = int(nentries)
        l_pr          = l_bc / nentries
        l_cn          = 0.5 * (l_ed[:-1] + l_ed[1:])
        arr_ext       = numpy.random.choice(l_cn, size=nentries, p=l_pr)
        arr_tot       = numpy.concatenate([arr_ext, arr_tot])

        return arr_tot
    #-----------------------------
    def _book_pdf(self, name=None, pdf=None, label=None, minx=None, maxx=None):
        arr_mas = numpy.linspace(minx, maxx, 500)
        arr_val = pdf.pdf(arr_mas) 

        plt.figure(name)
        plt.plot(arr_mas, arr_val, label=label)
    #-----------------------------
    def _book_histogram(self, name=None, binning=None, arr_val=None, label=None):
        plt.figure(name)
        plt.hist(arr_val, bins=binning, label=label, histtype='step', density=True)
    #-----------------------------
    def _get_pr_yield(self, proc=None, qsq=None):
        nevt = {
                'ctrl_jpsi' : self._npr_cc, 
                'ctrl_psi2' : self._npr_cp, 
                'psi2_jpsi' : self._npr_pc, 
                'psi2_psi2' : self._npr_pp, 
                }[f'{proc}_{qsq}']

        return nevt
    #-----------------------------
    @utnr.timeit
    def _plot_fit(self, proc):
        dat, pdf = self._d_pdf_dat[proc]

        zut.print_pdf(pdf, txt_path=f'{self._out_dir}/pdf_{proc}.txt')

        obj = zfp(data=dat, model=pdf)
        obj.plot(plot_range=self._plot_range, stacked=True, skip_pulls=True) 
        plt.savefig(f'{self._out_dir}/fit_{proc}.png')
    #-----------------------------
    def _save_figs(self):
        for fig_name in plt.get_figlabels():
            plt.figure(fig_name)
            plt.legend()
            plt.savefig(f'{self._out_dir}/{fig_name}.png')
#-----------------------------

