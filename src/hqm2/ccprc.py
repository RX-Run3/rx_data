import zfit
import numpy

from hqm2.data_store import data_store

#-----------------------------------
class ccprc:
    def __init__(self, obs=None, dset=None, preffix=None, syst=None, qsq_rng=None):
        self._obs   = obs
        self._dset  = dset 
        self._syst  = syst 
        self._pref  = preffix

        [self._qsq_src, self._qsq_tgt] = qsq_rng

        self._fft_npt = 1000
    #---------------------------------
    def _get_trf(self):
        mu      = zfit.param.Parameter(f'mu_trf_{self._pref}', 303, 0, 400)
        sg      = zfit.param.Parameter(f'sg_trf_{self._pref}',  40, 0, 100)
        al      = zfit.param.Parameter(f'al_trf_{self._pref}',-0.2,-1,  +1)
        nt      = zfit.param.Parameter(f'nt_trf_{self._pref}', 110, 0, 150)

        pdf_trf = zfit.pdf.CrystalBall(mu, sg, al, nt, obs=self._obs)

        return pdf_trf
    #---------------------------------
    def _get_muon_pdf(self):
        obj     = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc='data')
        arr_dat = obj.get_array(cuts={'SB' : 'B_M < 5180'})
        zdata   = zfit.Data.from_numpy(self._obs, array=arr_dat)
        pdf_mmd = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, name='data muon')

        return pdf_mmd
    #---------------------------------
    def _get_ratio(self):
        return 0.6
    #---------------------------------
    def _get_reso(self):
        mu      = zfit.param.Parameter(f'mu_res_{self._pref}', 5700, 5200, 6000)
        sg      = zfit.param.Parameter(f'sg_res_{self._pref}',   40,    0, 100)
        pdf_res = zfit.pdf.Gauss(obs=self._obs, mu=mu, sigma=sg)

        return pdf_res
    #---------------------------------
    def get_pdf(self):
        pdf_trf = self._get_trf()
        pdf_mmd = self._get_muon_pdf()
        r       = self._get_ratio()
        pdf_res = self._get_reso()

        pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_trf, kernel=pdf_mmd, name='PRc', n=self._fft_npt)
        pdf     = zfit.pdf.SumPDF([pdf_prc, pdf_res], r)

        return pdf
#-----------------------------------
