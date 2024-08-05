from log_store import log_store
import zfit

log=log_store.add_logger('rx_hqm2:signal')
#--------------------------------------------------------------------
class data:
    d_par         = dict()
    d_scale       = dict()

    d_par['dset'] = ['r1', 'r2p1', '2017', '2018']
    d_par['trig'] = ['MTOS', 'ETOS']
    d_par['syst'] = ['nom', 'alt']
#--------------------------------------------------------------------
def check_arg(name, value):
    if name not in data.d_par:
        log.error(f'Parameter {name} not found')
        raise

    l_val = data.d_par[name]
    if value not in l_val:
        log.error(f'Value {value} for {name} not among: {l_val}')
        raise
#--------------------------------------------------------------------
def check_args(skip=[]):
    def check_decorator(fun):
        def wrapper(**kwargs):
            for name, value in kwargs.items():
                if name in skip:
                    continue

                check_arg(name, value)

            val = fun(**kwargs)
            return val

        return wrapper

    return check_decorator
#--------------------------------------------------------------------
@check_args(skip=['prefix', 'obs'])
def get_signal(obs=None, dset=None, trig=None, prefix=None, syst=None):
    if trig == 'MTOS':
        pdf = _get_muon_signal(obs=obs, dset=dset, prefix=prefix, syst=syst)
    else:
        pdf = _get_electron_signal(obs=obs, dset=dset, prefix=prefix, syst=syst)

    pdf.dset = dset
    pdf.trig = trig 
    pdf.syst = syst 

    return pdf
#--------------------------------------------------------------------
def _get_muon_signal(obs=None, dset=None, prefix=None, syst=None):
    mu, sg = _get_peak_pars(prefix, dset, 'MTOS')
    if syst == 'nom':
        pdf = _get_dscb(mu, sg, prefix, obs)

    return pdf 
#--------------------------------------------------------------------
def _get_electron_signal(obs=None, dset=None, prefix=None, syst=None):
    pdf_z    = _get_electron_signal_brem(obs=obs, dset=dset, prefix=f'{prefix}_brem_0', syst=syst)
    pdf_o    = _get_electron_signal_brem(obs=obs, dset=dset, prefix=f'{prefix}_brem_1', syst=syst)
    pdf_t    = _get_electron_signal_brem(obs=obs, dset=dset, prefix=f'{prefix}_brem_2', syst=syst)

    fr_mc_z  = zfit.param.Parameter(f'fr_mc_z_{prefix}', 0, 0, 1)
    fr_mc_o  = zfit.param.Parameter(f'fr_mc_o_{prefix}', 0, 0, 1)
    fr_mc_t  = zfit.param.Parameter(f'fr_mc_t_{prefix}', 0, 0, 1)

    fr_sc_z  = zfit.param.Parameter(f'fr_sc_z_{prefix}', 1, 0, 2)
    fr_sc_o  = zfit.param.Parameter(f'fr_sc_o_{prefix}', 1, 0, 2)
    fr_sc_t  = zfit.param.Parameter(f'fr_sc_t_{prefix}', 1, 0, 2)

    fr_z     = zfit.ComposedParameter(f'fr_z_{prefix}' , func=lambda d_par : d_par['mc'] * d_par['sc'], params={'mc' : fr_mc_z, 'sc' : fr_sc_z} )
    fr_o     = zfit.ComposedParameter(f'fr_o_{prefix}' , func=lambda d_par : d_par['mc'] * d_par['sc'], params={'mc' : fr_mc_o, 'sc' : fr_sc_o} )
    fr_t     = zfit.ComposedParameter(f'fr_t_{prefix}' , func=lambda d_par : d_par['mc'] * d_par['sc'], params={'mc' : fr_mc_t, 'sc' : fr_sc_t} )

    pdf      = zfit.pdf.SumPDF([pdf_z, pdf_o, pdf_t], [fr_z, fr_o, fr_t])

    return pdf
#--------------------------------------------------------------------
def _get_electron_signal_brem(obs=None, dset=None, prefix=None, syst=None):
    mu, sg = _get_peak_pars(prefix, dset, 'ETOS')
    if syst == 'nom':
        pdf = _get_dscb(mu, sg, prefix, obs)

    return pdf
#--------------------------------------------------------------------
def _get_peak_pars(prefix, dset, trig):
    scale, resol = _get_scales(dset, trig)

    mu_mc = zfit.param.Parameter(f'mu_mc_{prefix}', 5200, 5200, 5400)
    mu    = zfit.ComposedParameter(f'mu_{prefix}' , func=lambda d_par : d_par['mc'] + d_par['sc'], params={'mc' : mu_mc, 'sc' : scale} )

    sg_mc = zfit.param.Parameter(f'sg_mc_{prefix}',   30,    5,  100)
    sg    = zfit.ComposedParameter(f'sg_{prefix}' , func=lambda d_par : d_par['mc'] * d_par['rs'], params={'mc' : sg_mc, 'rs' : resol} )

    return mu, sg
#--------------------------------------------------------------------
def _get_scales(dset, trig):
    key = f'{dset}_{trig}'
    if key in data.d_scale:
        return data.d_scale[key]

    scale = zfit.param.Parameter(f'sc_{dset}_{trig}', 10,  -30,   30)
    resol = zfit.param.Parameter(f'rs_{dset}_{trig}',  1,  0.8,  1.2)

    data.d_scale[key] = scale, resol

    return scale, resol
#--------------------------------------------------------------------
def _get_dscb(mu, sg, prefix, obs):
    al = zfit.param.Parameter(f'al_{prefix}', 0, 0,  5)
    nl = zfit.param.Parameter(f'nl_{prefix}', 0, 0, 10)
    ar = zfit.param.Parameter(f'ar_{prefix}', 0, 0,  5)
    nr = zfit.param.Parameter(f'nr_{prefix}', 0, 0, 10)

    pdf = zfit.pdf.DoubleCB(mu, sg, al, nl, ar, nr, obs)

    return pdf
#--------------------------------------------------------------------

