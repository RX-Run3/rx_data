import zfit

#-----------------------------------
class ccprc:
    def __init__(self, obs=None, dset=None, qsq=None, preffix=None, syst=None):
        self._obs = obs
        self._dset= dset 
        self._qsq = qsq 
        self._syst= syst 
        self._pref= preffix

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
    def _get_muon_data(self):
        pdf_mmd = zfit.pdf.Uniform(4250, 5180, self._obs)

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
        pdf_mmd = self._get_muon_data()
        r       = self._get_ratio()
        pdf_res = self._get_reso()

        pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_trf, kernel=pdf_mmd, name='PRc', n=self._fft_npt)
        pdf     = zfit.pdf.SumPDF([pdf_prc, pdf_res], r)

        return pdf
#-----------------------------------
