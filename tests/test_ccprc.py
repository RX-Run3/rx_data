from hqm2.ccprc   import ccprc 
from zutils.plot  import plot      as zfp
from log_store    import log_store

import zutils.utils      as zut
import matplotlib.pyplot as plt
import zfit
import os

#--------------------------------------------------
class data:
    obs = zfit.Space("B_M", limits=(0, 7000))
#-------------------------------------
def set_logs():
    log_store.set_level('scripts:zutils/utils'    , 30)
    log_store.set_level('rx_hqm2:data_store'      , 30)
    log_store.set_level('rx_scripts:storage/cache', 30)
    log_store.set_level('rx_scripts:atr_mgr:mgr'  , 30)
    log_store.set_level('tools:calc_utility'      , 40)
#--------------------------------------------------
def check_pdf(pdf, plot_dir, name='pdf', title=None):
    os.makedirs(plot_dir, exist_ok=True)

    zut.print_pdf(pdf, txt_path=f'{plot_dir}/{name}.txt')

    sam = pdf.create_sampler(n=10000)

    obj = zfp(data=sam, model=pdf)
    obj.plot(plot_range=(4500, 6000), stacked=True, skip_pulls=True, no_data=True) 

    ax=obj.axs[0]
    if title is not None:
        ax.set_title(title)

    ax.axvline(x=5280, color='r', linestyle=':')
    ax.set_ylim(bottom=0)
    plt.savefig(f'{plot_dir}/{name}.png')
    plt.close('all')
#--------------------------------------------------
def test_simple(dset):
    obj=ccprc(obs=data.obs, dset=dset, preffix=f'psi2_high_pr_{dset}', brem=None, syst='nom')
    pdf=obj.get_pdf()

    plot_dir = 'tests/ccprc/simple'
    check_pdf(pdf, plot_dir)
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

            brem     = 'int' if brem is None else f'cbrem_{brem}'
            plot_dir = f'tests/ccprc/all/{brem}/{dset}'
            check_pdf(pdf, plot_dir, title=f'Year:{dset}; Brem:{brem}')
#--------------------------------------------------
def main():
    set_logs()

    test_all()
    test_simple('2017')
    test_brem('2018', 1)
    test_brem('2018', 2)
#--------------------------------------------------
if __name__ == '__main__':
    main()

