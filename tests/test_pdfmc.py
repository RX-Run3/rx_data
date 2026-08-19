import zfit
import mplhep
import zutils.utils      as zut
import matplotlib.pyplot as plt

from hqm2.pdfmc  import pdfmc
from hqm2.config import Conf

from log_store   import log_store

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=[4500, 7000])
#-------------------------------------
def set_logs():
    log_store.set_level('scripts:zutils/utils'    , 20)
    log_store.set_level('rx_hqm2:data_store'      , 20)
    log_store.set_level('rx_scripts:storage/cache', 20)
    log_store.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    log_store.set_level('tools:calc_utility'      , 40)
#-------------------------------------
def test_brem_bin(ibin):
    Conf.fits['ntries'] = 10 

    Conf.binning['var'] =          'cbrem'
    Conf.binning['bin'] =            ibin
    Conf.binning['cut'] = f'cbrem=={ibin}'

    obj=pdfmc(obs=data.obs, dset='2018', proc='psi2', qsq='high')
    pdf=obj.get_pdf()

    zut.print_pdf(pdf)
    Conf.binning=dict()
#-------------------------------------
def test_psi2_high():
    obj=pdfmc(obs=data.obs, dset='2018', proc='psi2', qsq='high')
    pdf=obj.get_pdf()
    zut.print_pdf(pdf)
#-------------------------------------
def test_ctrl_psi2():
    obj=pdfmc(obs=data.obs, dset='2018', proc='ctrl', qsq='psi2')
    pdf=obj.get_pdf()
#-------------------------------------
def test_ctrl_jpsi():
    obj=pdfmc(obs=data.obs, dset='2018', proc='ctrl', qsq='jpsi')
    pdf=obj.get_pdf()
#-------------------------------------
def test_psi2_psi2():
    obj=pdfmc(obs=data.obs, dset='2018', proc='psi2', qsq='psi2')
    pdf=obj.get_pdf()
#-------------------------------------
def test_psi2_jpsi():
    obj=pdfmc(obs=data.obs, dset='2018', proc='psi2', qsq='jpsi')
    pdf=obj.get_pdf()
#-------------------------------------
def main():
    plt.style.use(mplhep.style.LHCb2)
    set_logs()

    test_brem_bin(0)
    test_brem_bin(1)
    test_brem_bin(2)
    test_psi2_high()

    test_ctrl_jpsi()
    test_ctrl_psi2()
    test_psi2_jpsi()
    test_psi2_psi2()
#-------------------------------------
if __name__ == '__main__':
    main()

