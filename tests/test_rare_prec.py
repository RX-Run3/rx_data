from hqm2.prec_rare import get_pdf as get_prec_rare_pdf 
from zutils.plot    import plot    as zfp

import matplotlib.pyplot as plt
import zfit
import os
#----------------------------------------
class data:
    obs     = zfit.Space('B_M', limits=[4000, 6000])
    out_dir = None
#----------------------------------------
def check_pdf(pdf, name='pdf'):
    arr_mas = pdf.arr_mas
    arr_wgt = pdf.arr_wgt
    zdata   = zfit.Data.from_numpy(data.obs, array=arr_mas, weights=arr_wgt)

    obj = zfp(data=zdata, model=pdf)
    obj.plot(nbins=50, stacked=False)
    ax = obj.axs[0]
    ax.set_title(f'Nentries: {arr_mas.size}')

    plt.savefig(f'{data.out_dir}/{name}.png')
#----------------------------------------
def test_simple(proc):
    pdf          = get_prec_rare_pdf(obs=data.obs, dset='2018', kind=proc, trig='ETOS') 
    data.out_dir = 'tests/prec_rare/simple'

    os.makedirs(data.out_dir, exist_ok=True)

    check_pdf(pdf, name=proc)
#----------------------------------------
def test_boots():
    data.out_dir = 'tests/prec_rare/boots'
    os.makedirs(data.out_dir, exist_ok=True)

    for bts in range(10):
        pdf = get_prec_rare_pdf(obs=data.obs, dset='2018', kind='bpks', trig='ETOS', bts=bts) 
        check_pdf(pdf, name=f'bts_{bts:03}')
#----------------------------------------
def test_brem(proc, cbrem):
    pdf          = get_prec_rare_pdf(obs=data.obs, dset='2018', kind=proc, trig='ETOS', brem=cbrem) 
    data.out_dir = 'tests/prec_rare/brem'

    os.makedirs(data.out_dir, exist_ok=True)

    check_pdf(pdf, name=f'{proc}_{cbrem}')
#----------------------------------------
def main():
    test_boots()

    test_simple('bsph')
    test_simple('bpks')
    test_simple('bdks')

    test_brem('bsph', 0)
    test_brem('bsph', 1)
    test_brem('bsph', 2)

    test_brem('bpks', 0)
    test_brem('bpks', 1)
    test_brem('bpks', 2)

    test_brem('bdks', 0)
    test_brem('bdks', 1)
    test_brem('bdks', 2)
#----------------------------------------
if __name__ == '__main__':
    main()

