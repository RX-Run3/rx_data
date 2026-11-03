#!/usr/bin/env python3

from rk.dilep_reso import plot_reso as rk_plot_reso

import utils_noroot as utnr
import os
import argparse
import numpy
import math

#----------------------------
class data:
    version = None
    inp_dir = None
    l_kind  = None
    l_dset  = None
    l_trig  = None
    l_brem  = None

    l_all_kind = ['data', 'mc']
    l_all_brem = ['0', '1', '2' ]
    l_all_dset = ['r1', 'r2p1', '2017', '2018' ]
    l_all_trig = ['ETOS', 'GTIS' ]

    l_par   = ['rsg', 'dmu', 'mMC', 'mDT']
    d_prange= { '0' : ( 10,  35), '1' : ( 20,  60), '2' : ( 30,  65) }
    d_rrange= { '0' : (120, 155), '1' : (130, 165), '2' : (115, 175) }

    log      = utnr.getLogger(__name__)
#----------------------------
def par_to_res(d_par):
    d_res = {}
    for sbin, d_fit_par in d_par.items():
        if 'inf' in sbin:
            continue

        if d_fit_par == {}:
            sg = numpy.nan
        else:
            [sg, _] = d_fit_par['sg']

        d_res[sbin] = sg

    return d_res
#----------------------------
def mask_empty(d_data):
    d_data_masked = {}

    for key, val in d_data.items():
        if isinstance(val, dict) or math.isnan(val):
            val = numpy.nan

        d_data_masked[key] = val

    return d_data_masked
#----------------------------
def plot_reso(kind, brem, par, trig, dset):
    par_path  = f'{data.inp_dir}/get_q2_resolutions/{kind}/json/{data.version}/{trig}_{dset}/{par}_brem_{brem}.json'
    data.log.info(f'Picking up parameters from: {par_path}')
    d_par_str = utnr.load_json(par_path)

    d_res_str = par_to_res(d_par_str)
    zrange    = data.d_prange[brem]

    d_res_str = mask_empty(d_res_str)
    plot_dir  = utnr.make_dir_path(f'{data.inp_dir}/get_q2_resolutions/plots/{data.version}/{trig}_{dset}')
    rk_plot_reso(d_res_str, plot_dir, suffix=f'{kind}_{brem}_{par}', title=f'Brem {brem}; From: {par},{kind}', rng=zrange)
#----------------------------
def plot_ratio(brem, par, trig, dset):
    json_path = f'{data.inp_dir}/get_q2_resolutions/ratio/{data.version}/{trig}_{dset}/{par}_brem_{brem}.json'
    data.log.info(f'Picking up parameters from: {json_path}')
    d_rat_str = utnr.load_json(json_path)
    if   par == 'rsg':
        zrange    = 0.5, 1.5
    elif par == 'dmu':
        zrange    = -30, +30
    elif par in ['mMC', 'mDT']:
        zrange    = 3030, 3110
    else:
        data.log.error(f'Invalid parameter: {par}')
        raise ValueError

    d_rat_str = mask_empty(d_rat_str)
    plot_dir  = utnr.make_dir_path(f'{data.inp_dir}/get_q2_resolutions/plots/{data.version}/{trig}_{dset}')
    rk_plot_reso(d_rat_str, plot_dir, suffix=f'rat_{brem}_{par}', title=f'Brem {brem}; From: {par}, ratio', rng=zrange)
#----------------------------
def plot_all_reso():
    return
    for kind in data.l_kind:
        for brem in data.l_brem:
            for par in data.l_par:
                for trig in data.l_trig:
                    for dset in data.l_dset:
                        plot_reso(kind, brem, par, trig, dset)
#----------------------------
def plot_all_ratios():
    for brem in data.l_brem:
        for par in data.l_par:
            for trig in data.l_trig:
                for dset in data.l_dset:
                    plot_ratio(brem, par, trig, dset)
#----------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to plot 2D maps of resolutions in data, MC and also their ratio')
    parser.add_argument('-v', '--vers', type=str , help='Version'      , required=True)
    parser.add_argument('-b', '--brem', nargs='+', help='Brem category', default=data.l_all_brem)
    parser.add_argument('-d', '--dset', nargs='+', help='Dataset'      , default=data.l_all_dset)
    parser.add_argument('-t', '--trig', nargs='+', help='Trigger'      , default=data.l_all_trig)
    parser.add_argument('-k', '--kind', nargs='+', help='Data or MC'   , default=data.l_all_kind)
    args = parser.parse_args()

    data.version = args.vers
    data.l_brem  = args.brem
    data.l_dset  = args.dset
    data.l_trig  = args.trig
    data.l_kind  = args.kind
    data.inp_dir = os.environ['QSQSYS']
#----------------------------
def main():
    get_args()

    plot_all_reso()
    plot_all_ratios()
#----------------------------
if __name__ == '__main__':
    main()

