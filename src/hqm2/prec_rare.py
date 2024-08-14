from hqm2.data_store import data_store
import zfit

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
def get_pdf(obs=None, dset=None, kind=None, trig=None, d_cut=dict()):
    obj     = data_store(qsq='high', dset=dset, trig=trig, proc=kind)
    arr_mas = obj.get_array(variable='B_M', d_cut = d_cut)

    bw      = get_bandwidth(arr_mas.size)

    zdata   = zfit.Data.from_numpy(obs, array=arr_mas)
    pdf     = zfit.pdf.KDE1DimFFT(obs=obs, data=zdata, bandwidth=bw, name=f'{kind}_{dset}_{trig}')
    pdf.arr_mas = arr_mas

    return pdf

