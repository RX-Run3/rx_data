#!/usr/bin/env python3

import utils_noroot as utnr

import argparse
import ROOT
import os

from rk.q2smear import q2smear as q2

import matplotlib.pyplot as plt
#------------------------------------
class data:
    log        = utnr.getLogger(__name__)

    l_year     = None
    l_trig     = None
    l_brem     = None
    cal_vers   = None

    l_all_year = ['2011', '2012', '2015', '2016', '2017', '2018']
    l_all_trig = ['ETOS', 'GTIS']
    l_all_brem = ['0', '1', '2']

    cal_dir    = os.environ['CALDIR']
    plot_dir   = utnr.make_dir_path('plots/check/smearing')
#------------------------------------
def get_rdf(year, trig, brem, mc=None):
    if mc not in [True, False]:
        data.log.error(f'RDF is neither MC nor data: {mc}')
        raise

    chan = 'mm'   if trig == 'MTOS' else   'ee'
    kind = 'ctrl' if mc             else 'data'

    file_path = f'cached/{year}_{trig}_{kind}_{chan}.root'
    utnr.check_file(file_path)

    rdf = ROOT.RDataFrame('tree', file_path)
    rdf = rdf.Define('yearLabbel',     year)
    rdf = rdf.Define('Jpsi_M'    , 'j_mass')
    rdf = rdf.Redefine('nbrem'   , 'if (nbrem > 1) return 2; else return int(nbrem);')
    rdf = rdf.Filter(f'nbrem == {brem}')

    rdf.treename = trig
    rdf.filepath = file_path

    return rdf
#------------------------------------
def check(year, trig, brem):
    rdf_mc = get_rdf(year, trig, brem, mc=True)
    rdf_dt = get_rdf(year, trig, brem, mc=False)

    arr_q2_dt = rdf_dt.AsNumpy(['j_mass'])['j_mass']
    arr_q2_or = rdf_mc.AsNumpy(['j_mass'])['j_mass']
    arr_q2_sm = get_q2(rdf_mc)

    plt.hist(arr_q2_or, bins=30, range=(2500, 3600), label='Original MC', histtype='step', density=True, color='blue')
    plt.hist(arr_q2_sm, bins=30, range=(2500, 3600), label='Smeared MC' , histtype='step', density=True, color='red')
    plt.hist(arr_q2_dt, bins=30, range=(2500, 3600), label='Data'       , histtype='step', density=True, color='black')

    plot_path = f'{data.plot_dir}/{trig}_{year}_{brem}.png'
    plt.legend()
    plt.title(f'{year}, {trig}, brem={brem}')
    plt.xlabel('$m(e^+,e^-)[MeV]$')
    plt.ylabel('Normalized')
    plt.savefig(plot_path)
    plt.close('all')
#------------------------------------
def get_q2(rdf):
    q2dir = f'{data.cal_dir}/qsq/{data.cal_vers}'

    obj         =q2(rdf, q2dir)
    arr_q2_smr  =obj.get_q2_smear(0)

    return arr_q2_smr
#------------------------------------
def main():
    for year in data.l_year:
        for trig in data.l_trig:
            for brem in data.l_brem:
                check(year, trig, brem)
#------------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to validate smearing factors by comparing smeared MC with data')
    parser.add_argument('-t', '--trig' , nargs='+', help='Trigger'               , default=data.l_all_trig, choices=data.l_all_trig)
    parser.add_argument('-y', '--year' , nargs='+', help='Year'                  , default=data.l_all_year, choices=data.l_all_year)
    parser.add_argument('-b', '--brem' , nargs='+', help='Bremstrahlung category', default=data.l_all_brem, choices=data.l_all_brem)
    parser.add_argument('-v', '--vers' , type =str, help='Version of scales, e.g. v1.nom', required=True, choices=['v1.nom', 'v2.nom', 'v3.nom'])
    args = parser.parse_args()

    data.l_year   = args.year
    data.l_trig   = args.trig
    data.l_brem   = args.brem
    data.cal_vers = args.vers
#------------------------------------
if __name__ == '__main__':
    get_args()
    main()

