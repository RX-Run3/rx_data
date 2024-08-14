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

    obj = zfp(data=arr_mas, model=pdf)
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
def test_brem_cut(proc, cbrem):
    d_cut=       {'brem' : f'cbrem=={cbrem}'}
    pdf          = get_prec_rare_pdf(obs=data.obs, dset='2018', kind=proc, trig='ETOS', d_cut=d_cut) 
    data.out_dir = 'tests/prec_rare/brem_cut'

    os.makedirs(data.out_dir, exist_ok=True)

    check_pdf(pdf, name=f'{proc}_{cbrem}')
#----------------------------------------
def main():
    test_simple('bsph')
    test_simple('bpks')
    test_simple('bdks')

    return

    test_brem_cut('bsph', 0)
    test_brem_cut('bsph', 1)
    test_brem_cut('bsph', 2)

    test_brem_cut('bpks', 0)
    test_brem_cut('bpks', 1)
    test_brem_cut('bpks', 2)

    test_brem_cut('bdks', 0)
    test_brem_cut('bdks', 1)
    test_brem_cut('bdks', 2)

    return


#----------------------------------------
if __name__ == '__main__':
    main()

