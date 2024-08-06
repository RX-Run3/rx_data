from hqm2.ccprc   import ccprc 
from zutils.plot  import plot      as zfp

import matplotlib.pyplot as plt
import zfit
import os

#--------------------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 6000))
#--------------------------------------------------
def check_pdf(pdf, plot_dir):
    os.makedirs(plot_dir, exist_ok=True)

    sam = pdf.create_sampler(n=10000)

    obj = zfp(data=sam, model=pdf)
    obj.plot(plot_range=(4500, 6000), stacked=True) 

    plt.savefig(f'{plot_dir}/pdf.png')
    plt.close('all')
#--------------------------------------------------
def test_simple():
    obj=ccprc(obs=data.obs, dset='2017', qsq='high', preffix='test_simple', syst='nom')
    pdf=obj.get_pdf()

    plot_dir = 'tests/ccprc/simple'
    check_pdf(pdf, plot_dir)
#--------------------------------------------------
def main():

    test_simple()
#--------------------------------------------------
if __name__ == '__main__':
    main()

