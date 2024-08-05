from hqm2.signal import get_signal

import zutils.utils   as zut
import zfit
import os

#-------------------------------------
class data:
    obs_ee = zfit.Space("B_M", limits=(4500, 6000))
    obs_mm = zfit.Space("B_M", limits=(5180, 5800))

    out_dir= 'tests/signal'
#-------------------------------------
def test_simple_mm():
    out_dir = f'{data.out_dir}/simple_mm'
    os.makedirs(out_dir, exist_ok=True)

    pdf = get_signal(obs=data.obs_mm, dset="2018", trig="MTOS", prefix="prefix", syst="nom")

    zut.print_pdf(pdf, txt_path=f'{out_dir}/pdf.txt')
#-------------------------------------
def test_simple_ee():
    out_dir = f'{data.out_dir}/simple_ee'
    os.makedirs(out_dir, exist_ok=True)

    pdf = get_signal(obs=data.obs_ee, dset="2018", trig="ETOS", prefix="prefix", syst="nom")

    zut.print_pdf(pdf, txt_path=f'{out_dir}/pdf.txt')
#-------------------------------------
def main():
    test_simple_mm()
    test_simple_ee()
#-------------------------------------
if __name__ == '__main__':
    main()

