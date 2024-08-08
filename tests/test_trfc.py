from hqm2.trfc    import trfc 
from zutils.plot  import plot      as zfp

import zutils.utils      as zut
import matplotlib.pyplot as plt
import mplhep
import zfit
import os

#--------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 7000))
#--------------------------------------
def test_high():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='high', proc='psi2', dset='2018', pref='psi2_high_pr')
    pdf_trf = obj.get_trf(plot_range=[5000, 7000])
#--------------------------------------
def test_psi2():
    obj     = trfc(obs=data.obs, qsq_src='psi2', qsq_tgt='psi2', proc='psi2', dset='2018', pref='psi2_psi2_pr')
    pdf_trf = obj.get_trf(plot_range=[4600, 5750])
#--------------------------------------
def main():
    plt.style.use(mplhep.style.LHCb2)

    test_psi2()
#--------------------------------------
if __name__ == '__main__':
    main()

