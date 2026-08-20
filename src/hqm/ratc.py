'''
File holding CCbarRatioCalculator and CCbarRatio classes
'''

import zfit
import numpy
import matplotlib.pyplot as plt

from typing         import Final
from pydantic       import BaseModel
from dmu.stats      import FitResult
from dmu.generic    import Serializable
from hqm.data_store import data_store
from hqm.config     import CCbarRatioCalculatorConf, TransferFunctionMakerConf 
from hqm.pdfmc      import pdfmc
from hqm.trfc       import TransferFunctionMaker
from rx_common      import Block, Channel, Component, Project, Qsq, Trigger
from dmu            import LogStore

log=LogStore.add_logger('hqm:ratc')

Loss = zfit.loss.ExtendedUnbinnedNLL
zpdf = zfit.pdf.BasePDF

_SOURCE_CHANNEL : Final[Channel] = Channel.mm # Channel used to get original part reco distribution
_TARGET_CHANNEL : Final[Channel] = Channel.ee # Channel where ratio will be extracted
#-----------------------------
class CCbarRatio(BaseModel, Serializable, frozen = True):
    '''
    Class representing ratio between fully and partly reconstructed charmonium
    '''
    res : FitResult
#-----------------------------
class CCbarRatioCalculator:
    '''
    Class that builds model using:
    - smeared muon data to represent electron partially reconstructed
    - Analytical PDF to represent fully reconstructed components

    it then uses the model to fit electron channel data and extract the ratios
    of fully reconstructed over partially reconstructed
    '''
    #-----------------------------
    def __init__(
        self, 
        cfg     : CCbarRatioCalculatorConf, 
        project : Project,
        block   : Block):
        '''
        Parameters
        ------------------
        cfg    : Object holding configuration
        block  : E.g. 1..8 
        project: E.g. rk or rkst
        '''
        self._cfg      = cfg
        self._project  = project
        self._block    = block 
        self._out_dir  = self._cfg.make_path(kind='ratios', project = project)
    #-----------------------------
    def __get_ratio(self) -> CCbarRatio:
        '''
        Returns
        -------------
        Object representing CCbarRatio
        '''
        nll_jpsi= self._get_nll(qsq = Qsq.jpsi)
        nll_psi2= self._get_nll(qsq = Qsq.psi2)

        nll     = nll_jpsi + nll_psi2
        res     = self._sim_fit(nll = nll)

        log.info('Plotting')
        self._plot_fit('psi2')
        self._plot_fit('ctrl')

        self._save_figs()

        log.info('Saving parameters')

        return CCbarRatio(res = res) 
    #-----------------------------
    def _get_nll(self, qsq : Qsq) -> Loss:
        '''
        Returns NLL for given q2 bin
        '''
        pdf   = self._get_model(qsq= qsq)
        array = self._get_data(qsq = qsq)
        zdat  = zfit.Data.from_numpy(obs=self._cfg.observable.fit_obs, array=array)

        if not isinstance(zdat, zfit.Data):
            raise ValueError('Dataset is not unbinned')

        nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=zdat)

        return nll
    #-----------------------------
    def _get_data(self, qsq : Qsq) -> numpy.ndarray:
        '''
        Parameters
        -----------------
        qsq: q2-bin

        Returns
        -----------------
        Array of masses for given q2-bin in real data
        '''
        trigger = Trigger.get_main_trigger(project = self._project, channel = _TARGET_CHANNEL)
        ds      = data_store(qsq=qsq, dset=self._block, trig=trigger, proc='data')
        array   = ds.get_array()

        return array
    #-----------------------------
    def _get_model(self, qsq : Qsq) -> zfit.pdf.SumPDF:
        r'''
        Parameters
        ---------------
        qsq: $q^2$ bin for which model is needed 

        Returns
        ---------------
        PDF with:

        - Part reco candidates with $J/\psi$ and $\psi(2S)$ decays
        - Fully reco candidates with same decays
        '''
        pdf_prjp = self._get_pr_pdf(comp = Component.bpkpjpsiee, qsq_tgt=qsq)
        pdf_prps = self._get_pr_pdf(comp = Component.bpkppsi2ee, qsq_tgt=qsq)

        pdf_psi2 = self._get_mc_pdf(comp = Component.bpkpjpsiee, qsq=qsq) 
        pdf_ctrl = self._get_mc_pdf(comp = Component.bpkppsi2ee, qsq=qsq) 

        pdf = zfit.pdf.SumPDF([
            pdf_prps,
            pdf_prjp, 
            pdf_psi2,
            pdf_ctrl, 
        ])

        return pdf
    #-----------------------------
    def _sim_fit(self, nll : Loss) -> FitResult:
        '''
        Parameters
        --------------
        nll: Negative log likelihood

        Returns
        --------------
        Result of fit
        '''
        log.info('Fitting')
        minimizer = zfit.minimize.Minuit()
        res       = minimizer.minimize(nll)
        res.hesse(method='minuit_hesse')

        obj = FitResult.from_zfit(res = res) 

        return obj 
    #-----------------------------
    def _get_mc_pdf(self, qsq_comp : Qsq, qsq_bin : Qsq) -> zpdf:
        comp= self._component_from_qsq(qsq = qsq_comp)
        obj = pdfmc(obs=self._cfg.observable.fit_obs, dset=self._block, comp=comp, qsq=qsq)
        pdf = obj.get_pdf()

        rat = self._cfg.parameters.get_ratio(qsq = qsq_bin)
        npr = self._cfg.parameters.get_part_reco_yield(qsq_comp = qsq_comp, qsq_bin = qsq_bin) 

        # nfully_reco = npart_reco / ratio
        nfr = zfit.ComposedParameter(f'nfr_{qsq_comp}_{qsq_bin}', func=lambda d_par : d_par['p1'] / d_par['p2'], params={'p1' : npr, 'p2' : rat} )

        pdf = pdf.create_extended(nfr, name= self._get_pdf_name(comp=comp, kind='fr'))

        return pdf
    #-----------------------------
    def _get_pdf_name(self, comp : Component, kind=None):
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

        return d_name[kind][comp]
    #-----------------------------
    def _get_pr_pdf(self, comp : Component, qsq_tgt : Qsq) -> zpdf:
        '''
        Parameters
        ------------------
        comp    : Component that has to be modelled, provides muon MC sample and source q2 bin for transfer function.
        qsq_tgt : q2 bin where PDF lives, target q2.

        Returns
        ------------------
        
        '''

        mas_cns   = {'psi2' : 'B_const_mass_psi2S_M', 'ctrl' : 'B_const_mass_M'}[comp]
        qsq_src   = {Component.bpkppsi2ee : Qsq.psi2, Component.bpkpjpsiee : Qsq.jpsi}[comp]

        cfg          = TransferFunctionMakerConf.load_bin_cfg(
            source   = qsq_src,
            target   = qsq_tgt,
            bin      = self._cfg.binning.bin,
            variable = self._cfg.binning.variable)

        obj       = TransferFunctionMaker(
            cfg    = cfg, 
            sample = comp,
            project= self._project, 
            block  = self._block)
        trf = obj.get_trf()

        trig      = Trigger.get_main_trigger(project = self._project, channel = _SOURCE_CHANNEL)
        obj       = data_store(qsq=qsq_src, dset=self._block, trig=trig, proc='data')
        arr_dt_mm = obj.get_array(variable='B_M', d_cut={'sb_mass' : f'{mas_cns} < {self._cfg.sb_mass}'})

        obs       = self._cfg.observable.fit_obs
        zdata     = zfit.Data.from_numpy(obs, array=arr_dt_mm)
        pdf_mm    = zfit.pdf.KDE1DimFFT(
            obs=obs, 
            data=zdata, 
            bandwidth=self._cfg.bandwidth, 
            name='PRec')

        name      = self._get_pdf_name(comp=comp, kind='pr')
        pdf_ee    = zfit.pdf.FFTConvPDFV1(
            func  = pdf_mm, 
            kernel= trf.pdf, 
            name  = name, 
            n     = self._cfg.fft_npt)

        nevt      = self._get_pr_yield(proc=comp, qsq=qsq_tgt)

        plt.title(f'Source $q^2$: {qsq_src}; Target $q^2$: {qsq_tgt}')

        pdf_ee.set_yield(nevt)

        return pdf_ee
    #-----------------------------
    def _book_pdf(self, name=None, pdf=None, label=None, minx=None, maxx=None):
        arr_mas = numpy.linspace(minx, maxx, 500)
        arr_val = pdf.pdf(arr_mas) 

        plt.figure(name, figsize=self._figsize)
        plt.plot(arr_mas, arr_val, label=label)
    #-----------------------------
    def _book_histogram(self, name=None, binning=None, arr_val=None, label=None):
        plt.figure(name, figsize=self._figsize)

        label = f'{label}; nev={arr_val.size}'
        plt.hist(arr_val, bins=binning, label=label, histtype='step', density=True)
    #-----------------------------
    def _plot_fit(self, proc):
        dat, pdf = self._d_pdf_dat[proc]

        zut.print_pdf(pdf, txt_path=f'{self._out_dir}/pdf_{proc}.txt')

        obj = zfp(data=dat, model=pdf)
        obj.plot(plot_range=self._plot_range, stacked=True, skip_pulls=True) 

        ax  = obj.axs[0]
        ax.set_ylim(bottom=0)
        self._add_title(ax)

        plt.savefig(f'{self._out_dir}/fit_{proc}.png')
    #-----------------------------
    def _add_title(self, ax):
        if len(Conf.binning) == 0:
            return

        cut = Conf.binning['cut']
        ax.set_title(cut)
    #-----------------------------
    def _save_figs(self):
        for fig_name in plt.get_figlabels():
            plt.figure(fig_name, self._figsize)
            plt.legend()
            plt.savefig(f'{self._out_dir}/{fig_name}.png')
    #-----------------------------
    def get_ratio(self) -> CCbarRatio:
        '''
        Returns
        -----------------
        Ratio of part reco over fully reco components
        '''
        json_path = self._out_dir / 'parameters.json'
        if json_path.exists():
            log.info(f'Parameters file found: {json_path}')
            rat = CCbarRatio.from_json(path = json_path)

            return rat 

        log.info('Parameters file not found, recalculating ratio')

        rat = self.__get_ratio()
        rat.to_json(path = json_path)

        return rat
#-----------------------------
