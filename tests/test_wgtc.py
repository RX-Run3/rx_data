from hqm2.data_store import data_store 
from hqm2.wgtc       import wgtc

import matplotlib.pyplot as plt
import numpy
import ROOT

#-------------------------------
def _get_real_rdf(proc=None):
    obj     = data_store(qsq='psi2', dset='2018', trig='ETOS', proc=proc)
    rdf     = obj.get_rdf(variables=['B_M', 'B_const_mass_M', 'B_const_mass_psi2S_M'])

    return rdf
#-------------------------------
def _get_rdf(kind=None):
    if   kind == 'data':
        arr_mass_noc = numpy.random.normal(5285, 50, 100000)
        arr_mass_ysc = numpy.random.normal(5280, 30, 100000)
    elif kind == 'mc':
        arr_mass_noc = numpy.random.normal(5290, 48, 100000)
        arr_mass_ysc = numpy.random.normal(5290, 20, 100000)
    else:
        log.error(f'Invalid kind: {kind}')
        raise

    d_data = {'B_M' : arr_mass_noc, 'B_const_mass_M' : arr_mass_ysc, 'B_const_mass_psi2S_M' : arr_mass_ysc}
    rdf    = ROOT.RDF.FromNumpy(d_data)

    return rdf
#-------------------------------
def _filter_array(arr, mrange):
    minm, maxm = mrange

    arr = arr[arr > minm]
    arr = arr[arr < maxm]

    return arr
#-------------------------------
def test_toy():
    mrange  = [5100, 5500]
    rdf_dt  = _get_rdf(kind='data')
    rdf_mc  = _get_rdf(kind='mc'  )

    arr_mas_dt  = numpy.random.normal(5285, 50, 100000)
    arr_mas_mc  = numpy.random.normal(5290, 48, 100000)
    arr_mas_mc  = _filter_array(arr_mas_mc, mrange)

    obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc, proc='psi2', mrange=mrange)
    obj.out_dir = 'tests/wgtc/toy'
    arr_wgt     = obj.get_weights(arr_mas=arr_mas_mc)

    plt.hist(arr_mas_dt, bins=30, range=mrange, histtype='step', label='Data')
    plt.hist(arr_mas_mc, bins=30, range=mrange, histtype='step', label=  'MC')
    plt.hist(arr_mas_mc, bins=30, range=mrange, histtype='step', label=  'Corrected', weights=arr_wgt)
    plt.legend()
    plot_path = f'tests/wgtc/toy/mass_test_dist.png'
    plt.savefig(plot_path)
    plt.close('all')
#-------------------------------
def test_real():
    rdf_dt  = _get_real_rdf(proc='data')
    rdf_mc  = _get_real_rdf(proc='psi2')
    arr_mas = numpy.random.uniform(4500, 6000, 10000)

    wrange      = [5000, 5500]
    obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc, proc='psi2', mrange=wrange)
    obj.out_dir = 'tests/wgtc/real'
    arr_wgt     = obj.get_weights(arr_mas=arr_mas)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 15))
    ax1.hist(arr_mas, range=[4500, 6000], label='No weights', histtype='step')
    ax1.hist(arr_mas, range=[4500, 6000], label='Weighted'  , weights=arr_wgt, alpha=0.5)
    ax1.axvline(x=wrange[0], linestyle=':', color='r')
    ax1.axvline(x=wrange[1], linestyle=':', color='r')
    ax1.legend()

    ax2.scatter(arr_mas, arr_wgt)
#-------------------------------
