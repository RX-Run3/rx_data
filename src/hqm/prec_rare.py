from hqm2.data_store import data_store
from hqm2.config     import Conf

import zfit
import numpy

#----------------------------------------------------------------------
def get_bandwidth(size):
    if 0 < size < 50:
        log.error(f'Cannot make KDE with {size} entries')
        raise

    if    50  < size <  200:
        return 15
    else:
        return 25 
#----------------------------------------------------------------------
def get_bts_wgt(arr_dat, lam=1, rseed=None):
    if rseed is None:
        return

    rng    = numpy.random.default_rng(seed=rseed)
    size   = len(arr_dat)
    arr_wgt= rng.poisson(lam, size=size)

    return arr_wgt 
#----------------------------------------------------------------------
def configure_brem(brem):
    if brem is None:
        return

    Conf.binning['var'] =          'cbrem'
    Conf.binning['bin'] =            brem 
    Conf.binning['cut'] = f'cbrem=={brem}'
#----------------------------------------------------------------------
def get_pdf_name(**kwargs):
    l_val = [ f'{key}_{val}' for key, val in kwargs.items() if val is not None ]

    return '_'.join(l_val)
#----------------------------------------------------------------------
def get_pdf(obs=None, dset=None, kind=None, trig=None, bts=None, brem=None):
    '''
    brem (int): 0, 1 or 2. If None (default) will return the PDF for all categories merged
    bts  (int): Bootstrapping index, used for systematics
    kind (str): Sample kind, bsph, bsks, bdks
    '''
    configure_brem(brem)

    obj     = data_store(qsq='high', dset=dset, trig=trig, proc=kind)
    arr_mas = obj.get_array(variable='B_M')
    arr_wgt = get_bts_wgt(arr_mas, rseed=bts)
    zdata   = zfit.Data.from_numpy(obs, array=arr_mas, weights=arr_wgt)

    bw      = get_bandwidth(arr_mas.size)
    name    = get_pdf_name(dset=dset, kind=kind, trig=trig, bts=bts, brem=brem)
    pdf     = zfit.pdf.KDE1DimFFT(obs=obs, data=zdata, bandwidth=bw, name=name)
    pdf.arr_mas = arr_mas
    pdf.arr_wgt = arr_wgt

    Conf.binning = dict()

    return pdf
#----------------------------------------------------------------------

