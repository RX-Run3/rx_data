from hqm2.wgtc import wgtc

import numpy
import ROOT

#-------------------------------
def get_rdf(kind=None):
    if   kind == 'data':
        arr_mass_noc = numpy.random.normal(5280, 50, 100000)
        arr_mass_ysc = numpy.random.normal(5280, 30, 100000)
    elif kind == 'mc':
        arr_mass_noc = numpy.random.normal(5290, 30, 100000)
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

    obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc)
    obj.out_dir = 'tests/wgtc/simple'
    arr_wgt     = obj.get_weights()
#-------------------------------
if __name__ == '__main__':
    test_simple()

