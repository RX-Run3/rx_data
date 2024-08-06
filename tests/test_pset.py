from hqm2.signal     import get_signal
from hqm2.par_setter import par_setter 
from hqm2.par_setter import log as par_logger 

import zutils.utils   as zut
import zfit
import os

#-------------------------------------
class data:
    obs_ee = zfit.Space("B_M", limits=(4500, 6000))
    obs_mm = zfit.Space("B_M", limits=(5180, 5800))

    out_dir= 'tests/par_setter'
#-------------------------------------
def test_simple_mm():
    out_dir = f'{data.out_dir}/simple_mm'
    os.makedirs(out_dir, exist_ok=True)


    pdf   = get_signal(obs=data.obs_mm, dset="2018", trig="MTOS", prefix="mc_fit_2018_MTOS", syst="nom")
    obj   = par_setter(pdf)
    pdf   = obj.pdf()
    d_cns = obj.constraints()

    zut.print_pdf(pdf, d_const = d_cns, txt_path=f'{out_dir}/pdf.txt')
#-------------------------------------
def test_simple_ee():
    out_dir = f'{data.out_dir}/simple_ee'
    os.makedirs(out_dir, exist_ok=True)

    pdf   = get_signal(obs=data.obs_ee, dset="2018", trig="ETOS", prefix="mc_fit_2018_ETOS", syst="nom")
    obj   = par_setter(pdf)
    pdf   = obj.pdf()
    d_cns = obj.constraints()

    zut.print_pdf(pdf,d_const = d_cns, txt_path=f'{out_dir}/pdf.txt')
#-------------------------------------
def test_brem_ee():
    out_dir = f'{data.out_dir}/brem_ee'
    os.makedirs(out_dir, exist_ok=True)

    pdf   = get_signal(obs=data.obs_ee, dset="2018", trig="ETOS", prefix="mc_fit_2018_ETOS", syst="nom")
    obj   = par_setter(pdf)

    for brem in [0, 1, 2]:
        pdf   = obj.pdf(brem=brem)
        d_cns = obj.constraints(brem=brem)

        zut.print_pdf(pdf,d_const = d_cns, txt_path=f'{out_dir}/pdf_brem_{brem}.txt')
#-------------------------------------
def main():
    par_logger.setLevel(10)

    test_brem_ee()
    test_simple_mm()
    test_simple_ee()
#-------------------------------------
if __name__ == '__main__':
    main()

