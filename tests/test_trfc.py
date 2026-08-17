
import zutils.utils      as zut
import matplotlib.pyplot as plt
import mplhep
import zfit

from hqm2.trfc    import trfc 
from hqm2.config  import config
from log_store    import log_store

#--------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 7000))
#--------------------------------------
def set_log():
    log_store.set_level('rx_scripts:zfitter'           , 20)
    log_store.set_level('rx_hqm2:trfc'                 , 10)
    log_store.set_level('rx_scripts:atr_mgr:mgr'       , 30)
    log_store.set_level('rx_scripts:atr_mgr:ldr'       , 30)
    log_store.set_level('rx_scripts:version_management', 30)
    log_store.set_level('tools:calc_utility'           , 30)
#--------------------------------------
def test_psi2_high_brem(ibin):
    config.fitting['ntries'] = 10 

    config.binning['var'] =          'cbrem'
    config.binning['bin'] =            ibin
    config.binning['cut'] = f'cbrem=={ibin}'

    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='high', proc='psi2', dset='2018', pref='psi2_high_pr_2018')
    pdf_trf = obj.get_trf()

    zut.print_pdf(pdf_trf)
    config.binning=dict()
#--------------------------------------
def test_psi2_high():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='high', proc='psi2', dset='2018', pref='psi2_high_pr_2018')
    obj.get_trf()
#--------------------------------------
def test_jpsi_high():
    obj     = trfc(obs=data.obs, qsq_src='jpsi', qsq_tgt='high', proc='ctrl', dset='comb', pref='jpsi_high_pr_comb')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_jpsi_jpsi():
    obj     = trfc(obs=data.obs, qsq_src='jpsi', qsq_tgt='jpsi', proc='ctrl', dset='2018', pref='jpsi_jpsi_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_jpsi_psi2():
    obj     = trfc(obs=data.obs, qsq_src='jpsi', qsq_tgt='psi2', proc='ctrl', dset='2018', pref='jpsi_psi2_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_psi2_jpsi():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='jpsi', proc='psi2', dset='2018', pref='psi2_jpsi_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def test_psi2_psi2():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='psi2', proc='psi2', dset='2018', pref='psi2_psi2_2018_pr')
    pdf_trf = obj.get_trf()
#--------------------------------------
def main():
    set_log()
    plt.style.use(mplhep.style.LHCb2)

    test_jpsi_high()
    test_psi2_high()

    test_psi2_high_brem(0)
    test_psi2_high_brem(1)
    test_psi2_high_brem(2)

    test_jpsi_jpsi()
    test_psi2_psi2()
    test_jpsi_jpsi()
    test_psi2_psi2()
    test_jpsi_jpsi()
    test_jpsi_psi2()
    test_psi2_jpsi()
#--------------------------------------
if __name__ == '__main__':
    main()

