from hqm2.data_store import data_store

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
def get_pdf(obs=None, dset=None, kind=None, trig=None, bts=None, brem=None):
    '''
    brem (int): 0, 1 or 2. If None (default) will return the PDF for all categories merged
    bts  (int): Bootstrapping index, used for systematics
    kind (str): Sample kind, bsph, bsks, bdks
    '''
    obj     = data_store(qsq='high', dset=dset, trig=trig, proc=kind)

    d_cut   = None if brem is None else {'brem' : f'cbrem=={brem}'}
    arr_mas = obj.get_array(variable='B_M', d_cut = d_cut)
    arr_wgt = get_bts_wgt(arr_mas, rseed=bts)
    zdata   = zfit.Data.from_numpy(obs, array=arr_mas, weights=arr_wgt)

    bw      = get_bandwidth(arr_mas.size)
    pdf     = zfit.pdf.KDE1DimFFT(obs=obs, data=zdata, bandwidth=bw, name=f'{kind}_{dset}_{trig}')
    pdf.arr_mas = arr_mas
    pdf.arr_wgt = arr_wgt

    return pdf
#----------------------------------------------------------------------

