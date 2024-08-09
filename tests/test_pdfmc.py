import zfit
import mplhep
import matplotlib.pyplot as plt

from hqm2.pdfmc import pdfmc

#-------------------------------------
class data:
    obs = zfit.Space('B_M', limits=[4500, 6000])
#-------------------------------------
def test_simple():
    obj=pdfmc(obs=data.obs, dset='2018', proc='ctrl', qsq='psi2')
    pdf=obj.get_pdf()
#-------------------------------------
def main():
    plt.style.use(mplhep.style.LHCb2)

    test_simple()
#-------------------------------------
if __name__ == '__main__':
    main()

