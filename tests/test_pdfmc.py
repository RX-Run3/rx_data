import zfit
import mplhep
import matplotlib.pyplot as plt

from hqm2.pdfmc import pdfmc

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=[4500, 6000])
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

    test_ctrl_jpsi()
    test_ctrl_psi2()
    test_psi2_jpsi()
    test_psi2_psi2()
#-------------------------------------
if __name__ == '__main__':
    main()

