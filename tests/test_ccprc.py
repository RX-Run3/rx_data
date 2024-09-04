import ROOT

from hqm2.ccprc   import ccprc 
from zutils.plot  import plot      as zfp
from log_store    import log_store

import matplotlib.pyplot as plt
import zutils.utils      as zut
import utils_noroot      as utnr 
import pprint
import mplhep
import numpy
import zfit
import os

#--------------------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 7000))
#-------------------------------------
def set_logs():
    log_store.set_level('scripts:zutils/utils'    , 20)
    log_store.set_level('rx_hqm2:data_store'      , 30)
    log_store.set_level('rx_scripts:storage/cache', 20)
    log_store.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    log_store.set_level('tools:calc_utility'      , 40)
#--------------------------------------------------
@utnr.timeit
def check_pdf(pdf, plot_dir, name='pdf', title=None, no_data=True, plot_range=(4000, 6000), d_leg=None):
    os.makedirs(plot_dir, exist_ok=True)

    zut.print_pdf(pdf, txt_path=f'{plot_dir}/{name}.txt')

    sam = pdf.create_sampler(n=10000)
    arr = sam.value().numpy().flatten()
    zdat= zfit.Data.from_numpy(pdf.space, array=arr)

    obj = zfp(data=zdat, model=pdf)
    obj.plot(plot_range=plot_range, stacked=True, skip_pulls=True, no_data=no_data, d_leg=d_leg) 

    ax=obj.axs[0]
    if title is not None:
        ax.set_title(title)

    ax.axvline(x=5280, color='r', linestyle=':')
    ax.set_ylim(bottom=0)
    plt.savefig(f'{plot_dir}/{name}.png')
    plt.close('all')
#--------------------------------------------------
def get_label(pdf):
    s_par = pdf.get_params(floating=None)
    [rpar]= [ par for par in s_par if par.name.startswith('r_psi2_') ]

    return rpar.label
#--------------------------------------------------
def plot_pdf(pdf, label=None):
    arr_mas = numpy.linspace(4000, 6000, 300)
    arr_pdf = pdf.pdf(arr_mas) 

    plt.plot(arr_mas, arr_pdf, label=label)
#--------------------------------------------------
def test_simple(dset):
    obj=ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', brem=None, syst='nom')
    pdf=obj.get_pdf()

    pprint.pprint(pdf.d_cns)

    plot_dir = 'tests/ccprc/simple'
    check_pdf(pdf, plot_dir)
#--------------------------------------------------
def test_jpsi(dset):
    obj=ccprc(obs=data.obs, dset=dset, preffix=f'jpsi_high_pr_{dset}', brem=None, syst='nom', qsq_src='jpsi')
    pdf=obj.get_pdf()

    pprint.pprint(pdf.d_cns)

    plot_dir = 'tests/ccprc/jpsi'
    d_leg    = {
            'CB_mc_ctrl_comb_high' : r'$B^+\to J/\psi(e^+e^-) K^+$',
            'PRec'                 : r'$B^+\to J/\psi(e^+e^-) + X$',
            }

    check_pdf(pdf, plot_dir, d_leg=d_leg, plot_range=[4000, 7000])
#--------------------------------------------------
def test_brem(dset, brem):
    obj =ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', syst='nom', brem=brem) 
    pdf =obj.get_pdf()

    plot_dir = 'tests/ccprc/brem'
    check_pdf(pdf, plot_dir, name=f'pdf_{brem}', title=f'Brem {brem}')
#--------------------------------------------------
def test_all():
    for dset in ['r1', 'r2p1', '2017', '2018']:
        for brem in [None, 1, 2]:
            obj=ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', brem=brem, syst='nom')
            pdf=obj.get_pdf()
            lab=get_label(pdf)

            brem     = 'int' if brem is None else f'cbrem_{brem}'
            plot_dir = f'tests/ccprc/all/{brem}/{dset}'
            check_pdf(pdf, plot_dir, title=f'Year:{dset}; Brem:{brem}; {lab}')
#--------------------------------------------------
def test_compare_brem(dset):
    for brem in [None, 1, 2]:
        obj =ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', syst='nom', brem=brem)
        pdf =obj.get_pdf()

        [pdf_prc, pdf_frc] = pdf.pdfs

        plt.figure('cc_prc')
        plot_pdf(pdf_prc, label=f'Brem: {brem}')

        plt.figure('cc_frc')
        plot_pdf(pdf_frc, label=f'Brem: {brem}')

    for fig_name in ['cc_prc', 'cc_frc']:
        plot_dir = f'tests/ccprc/compare_brem/{fig_name}'
        os.makedirs(plot_dir, exist_ok=True)

        plt.figure(fig_name)
        plt.ylim(bottom=0)
        plt.legend()
        plt.savefig(f'{plot_dir}/{dset}.png')
        plt.close()
#--------------------------------------------------
@utnr.timeit
def test_data_generation(dset):
    obj=ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', brem=None, syst='nom')
    pdf=obj.get_pdf()

    plot_dir = 'tests/ccprc/data_generation'
    check_pdf(pdf, plot_dir, no_data=False)
#--------------------------------------------------
def main():
    set_logs()
    plt.style.use(mplhep.style.LHCb2)

    set_logs()
    test_jpsi('comb')
    test_all()

    test_data_generation('2017')
    test_simple('2017')

    for dset in ['r1', 'r2p1', '2017', '2018']:
        test_compare_brem(dset)

    test_brem('2018', 1)
    test_brem('2018', 2)
#--------------------------------------------------
if __name__ == '__main__':
    main()

