from hqm2.data_store     import data_store
from hqm2.trfc           import trfc
from zutils.plot         import plot      as zfp
from importlib.resources import files
from log_store           import log_store

import os
import zfit
import utils_noroot as utnr
import zutils.utils as zut
import matplotlib.pyplot as plt

log=log_store.add_logger('rx_hqm2:ratc')
#-----------------------------
class ratc:
    def __init__(self, obs=None, dset=None):
        self._dset = dset
        self._obs  = obs

        self._plot_range = [4500, 6000]
        self._bandwidth  = 15
        self._fft_npt    = 1000
        self._d_pdf_dat  = dict() 

        self._rat_psi2 = zfit.param.Parameter('rat_psi2', 1, 0, 4)
        self._rat_ctrl = zfit.param.Parameter('rat_ctrl', 1, 0, 4)

        self._npr_psi2 = zfit.param.Parameter('npr_psi2', 1e3, 0, 1e6)
        self._npr_ctrl = zfit.param.Parameter('npr_ctrl', 1e3, 0, 1e6)
    #-----------------------------
    def get_ratio(self):
        json_path = files('hqm2_data').joinpath(f'ratios/{self._dset}/parameters.json')
        if os.path.isfile(json_path):
            log.info(f'Parameters file found: {json_path}')
            d_par = utnr.load_json(json_path)

            return d_par['rat_psi2']

        log.info('Parameters file not found, recalculating ratio')

        rat = self._get_ratio(json_path)

        return rat
    #-----------------------------
    def _get_ratio(self, json_path):
        nll_ctrl= self._get_nll('ctrl')
        nll_psi2= self._get_nll('psi2')
        nll     = nll_psi2 + nll_ctrl
        res     = self._sim_fit(nll)

        out_dir = os.path.dirname(json_path)
        os.makedirs(out_dir, exist_ok=True)

        self._save_fit(out_dir, 'psi2')
        self._save_fit(out_dir, 'ctrl')

        d_par = zut.fit_result_to_dict(res)
        utnr.dump_json(d_par, json_path)

        return d_par['rat_psi2']
    #-----------------------------
    def _get_nll(self, proc):
        qsq     = {'ctrl' : 'jpsi', 'psi2' : 'psi2'}[proc]

        ds      = data_store(qsq=qsq, dset=self._dset, trig='ETOS', proc='data')
        arr_dat = ds.get_array()
        pdf     = self._get_model(qsq=qsq)
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
    def _sim_fit(self, nll):
        minimizer = zfit.minimize.Minuit()
        res       = minimizer.minimize(nll)
        res.hesse(method='minuit_hesse')

        print(res)

        return res
    #-----------------------------
    def _get_mc_pdf(self, proc=None, qsq=None):
        json_path = files('hqm2_data').joinpath(f'fits/{proc}/{self._dset}_ETOS_{qsq}_{proc}.json')
        json_path = str(json_path)

        pdf = self._get_frec_model(proc, qsq) 
        if os.path.isfile(json_path):
            log.info(f'Found parameters for process={proc}, qsq={qsq}; not fitting')
            d_par = utnr.load_json(json_path)
            pdf   = zut.fix_pars(pdf, d_par, fix=True)

            return pdf

        log.info(f'Not found parameters for {proc}/{qsq} fitting')

        obj     = data_store(qsq=qsq, dset=self._dset, trig='ETOS', proc=proc)
        arr_dat = obj.get_array()

        plot_path = json_path.replace('.json', '.png')
        d_par     = zut.get_fit_pars(pdf, arr_dat, add_err=True, d_fit_opt = {'ntries' : 2}, d_plt_opt = {'plot_path' : plot_path, 'plot_range' : self._plot_range})

        d_par     = {key : val for key, val in d_par.items() if self._is_shape_par(key)}
        utnr.dump_json(d_par, json_path)
        pdf       = zut.fix_pars(pdf, d_par, fix=True)

        return pdf
    #-----------------------------
    def _is_shape_par(self, par_name):
        if par_name.startswith('nfr_'):
            return False

        if par_name.startswith('rat_'):
            return False

        if par_name.startswith('mu_'):
            return False

        if par_name.startswith('sg_'):
            return False

        return True
    #-----------------------------
    def _get_frec_model(self, proc, qsq):
        pdf = self._get_dscb(proc, qsq)
        rat = {'ctrl' : self._rat_ctrl, 'psi2' : self._rat_psi2}[proc]
        npr = {'ctrl' : self._npr_ctrl, 'psi2' : self._npr_psi2}[proc]
        nfr = zfit.ComposedParameter(f'nfr_{proc}_{qsq}', func=lambda d_par : d_par['p1'] / d_par['p2'], params={'p1' : npr, 'p2' : rat} )

        pdf = pdf.create_extended(nfr)

        return pdf
    #-----------------------------
    def _get_3cb(self, proc, qsq):
        mu  = zfit.param.Parameter( f'mu_{proc}_{qsq}', 5300, 5000, 5350)
        sg1 = zfit.param.Parameter(f'sg1_{proc}_{qsq}',  10, 2.0, 80)
        sg2 = zfit.param.Parameter(f'sg2_{proc}_{qsq}',  10, 2.0, 80)
        sg3 = zfit.param.Parameter(f'sg3_{proc}_{qsq}',  10, 2.0, 80)

        ar  = zfit.param.Parameter( f'ar_{proc}_{qsq}', -2, -6.0,  6.0)
        al  = zfit.param.Parameter( f'al_{proc}_{qsq}',  2, -6.0,  6.0)
        ac  = zfit.param.Parameter( f'ac_{proc}_{qsq}',  2, -6.0,  6.0)
    
        nr  = zfit.param.Parameter( f'nr_{proc}_{qsq}', 1, 0.5, 8) 
        nl  = zfit.param.Parameter( f'nl_{proc}_{qsq}', 2, 0.5, 8) 
        nc  = zfit.param.Parameter( f'nc_{proc}_{qsq}', 3, 0.5, 8) 
    
        cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, self._obs, name='CB1')
        cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, self._obs, name='CB2')
        cb3 = zfit.pdf.CrystalBall(mu, sg3, ac, nc, self._obs, name='CB3')

        f_1 = zfit.param.Parameter(f'frc_1_{proc}_{qsq}', 0.5, 0, 1) 
        f_2 = zfit.param.Parameter(f'frc_2_{proc}_{qsq}', 0.5, 0, 1) 
        f_3 = zfit.param.Parameter(f'frc_3_{proc}_{qsq}', 0.5, 0, 1) 

        pdf = zfit.pdf.SumPDF([cb1, cb2, cb3], [f_1, f_2, f_3])

        return pdf
    #-----------------------------
    def _get_dscb(self, proc, qsq):
        mu  = zfit.param.Parameter(f'mu_dscb_{proc}_{qsq}' , 5100, 5000, 5500)
        sg  = zfit.param.Parameter(f'sg_dscb_{proc}_{qsq}' ,   10,    2,   80)
        ar  = zfit.param.Parameter(f'ar_dscb_{proc}_{qsq}' ,    1,    0,    5)
        al  = zfit.param.Parameter(f'al_dscb_{proc}_{qsq}' ,    1,    0,    5)
        nr  = zfit.param.Parameter(f'nr_dscb_{proc}_{qsq}' ,    2,    1,   20)
        nl  = zfit.param.Parameter(f'nl_dscb_{proc}_{qsq}' ,    2,    0,   20)
    
        pdf = zfit.pdf.DoubleCB(mu, sg, al, nl, ar, nr, self._obs, name='DSCB')

        return pdf
    #-----------------------------
    def _get_pr_pdf(self, proc=None, qsq=None):
        '''
        proc(str): Component that has to be modelled, provides muon MC sample and source q2 bin for transfer function.
        qsq (str): q2 bin where PDF lives, target q2.
        '''

        qsq_src = {'psi2' : 'psi2', 'ctrl' : 'jpsi'}[proc]
        obj     = trfc(obs=self._obs, qsq_src=qsq_src, qsq_tgt=qsq, proc=proc, dset=self._dset, pref=f'{qsq_src}_{qsq}_pr')
        pdf_trf = obj.get_trf()

        obj       = data_store(qsq=qsq, dset=self._dset, trig='MTOS', proc='data')
        arr_dt_mm = obj.get_array()

        zdata     = zfit.Data.from_numpy(self._obs, array=arr_dt_mm)
        pdf_mm    = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bandwidth, name='PRec')
        pdf_ee    = zfit.pdf.FFTConvPDFV1(func=pdf_mm, kernel=pdf_trf, name=f'PRec {proc} -> {qsq}', n=self._fft_npt)

        nevt      = {'ctrl' : self._npr_ctrl, 'psi2' : self._npr_psi2}[proc]
        pdf_ee.set_yield(nevt)

        return pdf_ee
    #-----------------------------
    def _save_fit(self, out_dir, proc):
        dat, pdf = self._d_pdf_dat[proc]

        zut.print_pdf(pdf, txt_path=f'{out_dir}/pdf_{proc}.txt')

        obj = zfp(data=dat, model=pdf)
        obj.plot(plot_range=self._plot_range, stacked=False) 

        plt.savefig(f'{out_dir}/fit_{proc}.png')
        plt.close('all')
#-----------------------------

