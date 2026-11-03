import os
import matplotlib.pyplot as plt

from logzero       import logger as log
from zutils.plot   import plot   as zfp
from q2_syst.model import model  as q2model
from fitter        import zfitter

#-------------------------------
def plot_model(pdf, name):
    dir_name = 'tests/model'
    os.makedirs(dir_name, exist_ok=True)

    dat= pdf.create_sampler(n=10000)
    ftr=zfitter(pdf, dat)
    res=ftr.fit()

    obj= zfp(data=dat, model=pdf, result=res)
    obj.plot()
    plt.savefig(f'{dir_name}/{name}.png')
    plt.close('all')
#-------------------------------
def get_sim_par():
    d_sim_par = {}
    d_sim_par['mu_1'] = [3100, 0]
    d_sim_par['mu_2'] = [3100, 0]
    d_sim_par['mu_3'] = [3100, 0]

    d_sim_par['sg_1'] = [10, 0]
    d_sim_par['sg_2'] = [10, 0]
    d_sim_par['sg_3'] = [10, 0]

    return d_sim_par
#-------------------------------
def test_1():
    obj=q2model()
    pdf=obj.get_pdf(is_signal=False, split_by_nspd=False)

    plot_model(pdf, 'test_1')
    log.info('Passed test_1')
    obj.clean_pars()
#-------------------------------
def test_2():
    obj=q2model()
    pdf=obj.get_pdf(is_signal=True, split_by_nspd=False)

    plot_model(pdf, 'test_2')
    log.info('Passed test_2')
    obj.clean_pars()
#-------------------------------
def test_3():
    d_sim_par = get_sim_par()

    obj=q2model(d_sim_par=d_sim_par)
    pdf=obj.get_pdf(is_signal=False, split_by_nspd=True)

    plot_model(pdf, 'test_3')
    log.info('Passed test_3')
    obj.clean_pars()
#-------------------------------
def main():
    test_1()
    test_2()
    test_3()
#-------------------------------
if __name__ == '__main__':
    main()

