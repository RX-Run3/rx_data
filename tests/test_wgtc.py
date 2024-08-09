from hqm2.wgtc import wgtc

import matplotlib.pyplot as plt
import numpy
import ROOT

#-------------------------------
def get_rdf(kind=None):
    if   kind == 'data':
        arr_mass_noc = numpy.random.normal(5285, 50, 100000)
        arr_mass_ysc = numpy.random.normal(5280, 30, 100000)
    elif kind == 'mc':
        arr_mass_noc = numpy.random.normal(5290, 48, 100000)
        arr_mass_ysc = numpy.random.normal(5290, 20, 100000)
    else:
        log.error(f'Invalid kind: {kind}')
        raise

    d_data = {'B_M' : arr_mass_noc, 'B_const_mass_M' : arr_mass_ysc}
    rdf    = ROOT.RDF.FromNumpy(d_data)

    return rdf
#-------------------------------
def test_simple():
    rdf_dt  = get_rdf(kind='data')
    rdf_mc  = get_rdf(kind='mc'  )

    arr_mas_dt  = numpy.random.normal(5285, 50, 100000)
    arr_mas_mc  = numpy.random.normal(5290, 48, 100000)

    obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc)
    obj.out_dir = 'tests/wgtc/simple'
    arr_wgt     = obj.get_weights(arr_mas=arr_mas_mc)

    plt.hist(arr_mas_dt, bins=30, range=[5000, 5600], histtype='step', label='Data')
    plt.hist(arr_mas_mc, bins=30, range=[5000, 5600], histtype='step', label=  'MC')
    plt.hist(arr_mas_mc, bins=30, range=[5000, 5600], histtype='step', label=  'Corrected', weights=arr_wgt)
    plt.legend()
    plot_path = f'tests/wgtc/simple/mass_test_dist.png'
    plt.savefig(plot_path)
    plt.close('all')
#-------------------------------
if __name__ == '__main__':
    test_simple()

