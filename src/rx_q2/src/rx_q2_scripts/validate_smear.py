#!/usr/bin/env python3

import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow_addons")

import ROOT
import glob
import utils
import numpy
import pprint
import mplhep
import numexpr
import logging
import logzero
import argparse
import utils_noroot      as utnr
import matplotlib.pyplot as plt
import read_selection    as rs
import rk.calc_utility   as rkcu

from rk.wgt_mgr    import wgt_mgr
from rk.q2smear    import q2smear as q2smr
from q2_syst.model import model   as q2model
from logzero       import logger  as log

#-----------------------------------
class data:
    pdf    = None
    vers   = None
    qsq_dir= None
    cas_dir= None
    cal_dir= None
    nevs   = None
    mcvers = None

    plot_dir= None
    diag_dir= None

    l_year = None
    l_trig = None
    l_brem = None
    nbins  = 100

    l_all_trig = ['ETOS', 'GTIS']
    l_all_brem = ['0', '1', '2']
    l_all_year = ['r1', 'r2p1', '2017', '2018']
#-------------------
def get_wgt_syst(trigger):
    '''Will return systematic for L0 and GEN weights corresponding to _cal_sys [nom, 000]
    '''
    gen_syst = 'MTOS'

    if   trigger == 'MTOS':
        lzr_syst = 'L0MuonTIS'
    elif trigger == 'ETOS':
        lzr_syst = 'L0ElectronTIS'
    elif trigger == 'GTIS':
        lzr_syst = 'L0TIS_EMMH.L0HadronElEL.L0ElectronTIS'
    else:
        log.error(f'Invalid HLT tag: {trigger}')
        raise

    hlt_syst = trigger

    return gen_syst, lzr_syst, hlt_syst, hlt_syst
#-----------------------------------
def add_cal_wgt(rdf, trig, year, brem):
    identifier   = f'{trig}_{year}_{brem}'
    rdf.filepath = 'no-path'
    rdf.treename = trig
    rdf.trigger  = trig
    rdf.year     = year

    d_set            = {}
    d_set['val_dir'] = f'{data.plot_dir}/cal_wgt_{identifier}'
    d_set['replica'] = 0
    d_set['bts_ver'] ='10'
    d_set['bts_sys'] ='nom'
    d_set['pid_sys'] ='nom'
    d_set['trk_sys'] ='nom'
    d_set['gen_sys'] ='nom'
    d_set['lzr_sys'] ='nom'
    d_set['hlt_sys'] ='nom'
    d_set['rec_sys'] ='nom'

    obj         = wgt_mgr(d_set)
    obj.log_lvl = logging.WARNING
    rsl         = obj.get_reader('sel', rdf)

    gen_syst, lzr_syst, hlt_syst, rec_syst = get_wgt_syst(trig)

    arr_pid     = rsl('pid', 'nom')
    arr_trk     = rsl('trk', 'nom')
    arr_gen     = rsl('gen', gen_syst)
    arr_lzr     = rsl('lzr', lzr_syst)
    arr_hlt     = rsl('hlt', hlt_syst)
    arr_rec     = rsl('rec', rec_syst)

    arr_cal = arr_pid * arr_trk * arr_gen * arr_lzr * arr_hlt * arr_rec
    rdf     = utils.add_df_column(rdf, arr_cal,  'weight', d_opt={'exclude_re' : 'tmva_.*'})

    return rdf
#-----------------------------------
def plot_wgt(rdf, title, name):
    plot_path = f'{data.diag_dir}/{name}'
    arr_wgt   = rdf.AsNumpy(['weight'])['weight']
    mean      = numpy.mean(arr_wgt)

    log.visible(f'Saving to: {plot_path}')

    plt.hist(arr_wgt, 40, range=(0, 2.0), histtype='step', density=True)
    plt.xlabel('Weight')
    plt.ylabel('Normalized')
    plt.title(f'$\mu={mean:.3f}$; {title}')
    plt.savefig(plot_path)
    plt.close('all')
#-----------------------------------
def get_data_paths(year, trig):
    if   year == 'r1':
        l_data_wc = [
                f'{data.cas_dir}/tools/apply_selection/q2_smear/ctrl/{data.mcvers}/2011_{trig}/*.root',
                f'{data.cas_dir}/tools/apply_selection/q2_smear/ctrl/{data.mcvers}/2012_{trig}/*.root']
    elif year == 'r2p1':
        l_data_wc = [
                f'{data.cas_dir}/tools/apply_selection/q2_smear/ctrl/{data.mcvers}/2015_{trig}/*.root',
                f'{data.cas_dir}/tools/apply_selection/q2_smear/ctrl/{data.mcvers}/2016_{trig}/*.root']
    elif year in ['2017', '2018']:
        l_data_wc = [f'{data.cas_dir}/tools/apply_selection/q2_smear/ctrl/{data.mcvers}/{year}_{trig}/*.root']
    else:
        log.error(f'Invalid year: {year}')
        raise

    l_data_path = []
    for data_wc in l_data_wc:
        l_data_path += glob.glob(data_wc)

    if len(l_data_path) == 0:
        log.error('Cannot find data in:')
        pprint.pprint(l_data_wc)
        raise

    return l_data_wc
#-----------------------------------
def get_rdf(trig, year, nbrem):
    l_data_path= get_data_paths(year, trig)
    bdt_cut    = rs.get('bdt', trig, q2bin='none', year='none')

    rdf = ROOT.RDataFrame(trig, l_data_path)
    if data.nevs > 0:
        total = rdf.Count().GetValue()
        log.warning(f'Picking up {data.nevs}/{total} events')
        rdf = rdf.Filter(f'rdfentry_ < {data.nevs}')

    rdf=rdf.Define('brem_mult', 'L1_BremMultiplicity + L2_BremMultiplicity')
    rdf=rdf.Define('nbrem'    , 'brem_mult < 2 ? brem_mult : 2')
    rdf=rdf.Filter(f'nbrem == {nbrem}', 'BREM')
    rdf=rdf.Filter(bdt_cut            ,  'BDT')
    rdf.q2  = 'jpsi'
    rdf.trig= trig
    rdf     = rkcu.addDiffVars(rdf)

    if not data.wgts:
        log.warning('Using PID weights from simulation only')
        pid_cut = rs.get('pid', trig, 'jpsi', year)
        rdf=rdf.Define('weight', f'float({pid_cut} == 1)')
    else:
        log.info('Calculating calibration weights')
        rdf=add_cal_wgt(rdf, trig, year, nbrem)

    if data.debug:
        rep=rdf.Report()
        rep.Print()

    rdf.treename = trig

    name    = f'wgt_{trig}_{year}_{nbrem}.png'
    title   = f'Trig: {trig}; Year: {year}; Brem: {nbrem}; Vers: {data.vers}'
    plot_wgt(rdf, title, name)

    return rdf
#-----------------------------------
def get_res_val(res, l_par):
    l_name    = [name for name in res.params]
    l_value   = res.values
    d_par_val = dict(zip(l_name, l_value))

    return {name : val for name, val in d_par_val.items() if name in l_par}
#-----------------------------------
def get_pdf(trig, year, nbrem):
    log.info('Getting PDF')

    vers         = data.vers.replace('.mom', '.nom')
    dat_res_path = f'{data.qsq_dir}/get_q2_tables/fits/{vers}/dat_{trig}_{year}_{nbrem}_nom.pkl'
    sim_res_path = f'{data.qsq_dir}/get_q2_tables/fits/{vers}/sim_{trig}_{year}_{nbrem}_nom.pkl'

    sim_res = utnr.load_pickle(sim_res_path)
    dat_res = utnr.load_pickle(dat_res_path)

    d_sim_par = get_res_val(sim_res, ['ap_l', 'pw_l', 'ap_r', 'pw_r', 'ncbr', 'ncbl'])
    d_dat_par = get_res_val(dat_res, ['mu', 'sg'])
    d_par     = d_sim_par | d_dat_par

    s_param   = data.pdf.get_params()

    for par in s_param:
        if par.name not in d_par:
            log.error(f'PDF parameter {par.name} not found in')
            pprint.pprint(d_par)
            raise

        val = d_par[par.name]
        par.set_value(val)
        log.debug(f'{par.name:<20}{"->":<20}{val:20.3f}')

    return data.pdf
#-----------------------------------
def get_efficiency(arr_qsq, trig, year):
    cut = rs.get('q2', trig, 'jpsi', year)
    cut = cut.replace('&&', '&')

    arr_flg = numexpr.evaluate(cut, {'Jpsi_M' : arr_qsq})
    arr_pas = arr_qsq[arr_flg]

    return arr_pas.size / arr_qsq.size
#-----------------------------------
def normalize_weights(arr_mass, arr_wgt):
    l_count, l_bin = numpy.histogram(arr_mass, bins=100, range=(1000, 4000), weights=arr_wgt)
    ncount         = sum(l_count)
    width          = l_bin[1] - l_bin[0]
    area           = ncount * width
    arr_wgt        = arr_wgt / area

    return arr_wgt
#-----------------------------------
def plot_dist(arr_smr, arr_org, arr_wgt, pdf, trig, year, nbrem):
    arr_x = numpy.linspace(data.min_mass, data.max_mass, 400)
    arr_y = data.pdf.pdf(arr_x)

    eff_smr = get_efficiency(arr_smr, trig, year)
    eff_org = get_efficiency(arr_org, trig, year)
    header  = f'Eff:{eff_org:.3f} -> {eff_smr:.3f}'

    #arr_wgt = normalize_weights(arr_org, arr_wgt)

    plt.subplots(figsize=(10,7))
    plt.plot(arr_x, arr_y, '-', label='Data', color='black')
    plt.hist(arr_org, data.nbins, weights=arr_wgt, range=(data.min_mass, data.max_mass), histtype='step', label='Original', density=True)
    plt.hist(arr_smr, data.nbins, weights=arr_wgt, range=(data.min_mass, data.max_mass), histtype='step', label='Smeared' , density=True)

    title   = f'Trig: {trig}; Year: {year}; Brem: {nbrem}; Vers: {data.vers}'
    name    = f'{trig}_{year}_{nbrem}.png'

    plot_path = f'{data.plot_dir}/{name}'
    log.info(f'Saving to: {plot_path}')

    plt.legend(title=header)
    plt.grid()
    plt.title(title)
    plt.xlabel('$M(J/\psi)$')
    plt.ylabel('Normalized')
    plt.savefig(plot_path)
    plt.close('all')
#-----------------------------------
def validate(trig, year, nbrem):
    rdf = get_rdf(trig, year, nbrem)
    pdf = get_pdf(trig, year, nbrem)

    q2dir   = f'{data.cal_dir}/qsq/{data.vers}'

    smr         = q2smr(rdf, q2dir)
    smr.out_dir = data.plot_dir
    arr_smr = smr.get_q2_smear(0)
    arr_org = rdf.AsNumpy(['Jpsi_M'])['Jpsi_M']
    arr_wgt = rdf.AsNumpy(['weight'])['weight']

    plot_dist(arr_smr, arr_org, arr_wgt, pdf, trig, year, nbrem)
#-----------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to compare smeared MC with fitted data')
    parser.add_argument('-v', '--vers' , type=str, help='Version of smearing parameters and corresponding fits', required=True)
    parser.add_argument('-s', '--simv' , type=str, help='Version of MC used to smear while validating'         , required=True)
    parser.add_argument('-y', '--year' , nargs='+', help='Years'        , choices=data.l_all_year, default=data.l_all_year)
    parser.add_argument('-t', '--trig' , nargs='+', help='Triggers'     , choices=data.l_all_trig, default=data.l_all_trig)
    parser.add_argument('-b', '--brem' , nargs='+', help='Brem category', choices=data.l_all_brem, default=data.l_all_brem)
    parser.add_argument('-d', '--debug', help='Will run in debug mode'  , action='store_true')
    parser.add_argument('-w', '--wgts' , help='Will use calibration weights on simulation, instead of PID cut', action='store_true')
    parser.add_argument('-e', '--nevs' , type =int, help='Number of entries to run over', default=-1)
    parser.add_argument('-c', '--cdir' , type =str, help='Directory with calibration maps')
    args = parser.parse_args()

    data.vers   = args.vers
    data.mcvers = args.simv
    data.nevs   = args.nevs
    data.wgts   = args.wgts
    data.l_year = args.year
    data.l_trig = args.trig
    data.l_brem = args.brem

    data.qsq_dir = get_env_var('QSQSYS')
    data.cas_dir = get_env_var('CASDIR')
    data.cal_dir = get_env_var('CALDIR') if args.cdir is None else args.cdir

    mdl           = q2model()
    data.pdf      = mdl.get_pdf(is_signal=True, split_by_nspd=False)
    [[data.min_mass]], [[data.max_mass]] = data.pdf.space.limits

    plt.style.use(mplhep.style.LHCb2)

    data.debug = args.debug
    if args.debug:
        log.setLevel(logzero.DEBUG)
    else:
        log.setLevel(logzero.INFO)

    data.plot_dir = utnr.make_dir_path(f'{data.qsq_dir}/validate_smear/{data.vers}')
    data.diag_dir = utnr.make_dir_path(f'{data.qsq_dir}/validate_smear/{data.vers}/diagnostics')
#-----------------------------------
def get_env_var(varname):
    try:
        value = os.environ[varname]
    except:
        log.error(f'Cannot find {varname} variable in environment')
        raise

    return value
#-----------------------------------
def main():
    for year in data.l_year:
        for trig in data.l_trig:
            for brem in data.l_brem:
                validate(trig, year, brem)
#-----------------------------------
if __name__ == '__main__':
    get_args()
    main()

