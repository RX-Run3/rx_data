#!/usr/bin/env python3

import os
import re
import argparse

import pandas            as pnd
import utils_noroot      as utnr
import matplotlib.pyplot as plt
#-----------------------------------------
class data:
    log      = utnr.getLogger(__name__)
    l_trig   = ['ETOS', 'GTIS', 'AVRG']
    l_brem   = ['0', '1', '2']
    l_year   = ['r1', 'r2p1', '2017', '2018']
    l_par    = ['delta_m', 'mu_MC', 's_sigma']

    plot_dir = None
    qsq_dir  = os.environ['QSQSYS']
    version  = None

    d_range  = {'delta_m' : (-20, +20), 'mu_MC' : (3050, 3100), 's_sigma' : (0.90, 1.30) }
    d_trigger= {'AVRG' : 'Average', 'ETOS' : 'eTOS', 'GTIS' : 'gTIS!'}
    d_yname  = {'mu_MC': r'$\mu_{MC}$', 'delta_m' : r'$\Delta M$', 's_sigma' : r'$s_{\sigma}$'}
#-----------------------------------------
def get_pars(vers, trig, brem, year):
    cal_dir = os.environ['CALDIR']
    d_par   = utnr.load_json(f'{cal_dir}/qsq/{vers}/{year}.json')
    regex   = f'{trig}\s([\w,_]+)\s{brem}\sgamma'
    d_res   = dict(d_par)

    for key in d_par:
        mtch=re.match(regex, key)
        if not mtch:
            del(d_res[key])
            continue

        obj        = d_res[key]
        [val, err] = obj if isinstance(obj, list) else [obj, 0]
        var        = mtch.group(1)

        del(d_res[key])
        d_res[var] = [val, err]

    d_res = dict(sorted(d_res.items()))

    return d_res
#-----------------------------------------
def get_rows(trig, brem, year):
    l_row = []
    for vers in [data.version]:
        d_par=get_pars(vers, trig, brem, year)

        for var, [val, err] in d_par.items():
            row=[year, brem, trig, var, val, err]
            l_row.append(row)

    return l_row
#-----------------------------------------
def get_df():
    df = pnd.DataFrame(columns=['year', 'brem', 'trig', 'par_name', 'par_val', 'par_err'])
    for trig in data.l_trig:
        for brem in data.l_brem:
            for year in data.l_year:
                l_row= get_rows(trig, brem, year)
                df   = utnr.add_rows_to_df(df, l_row)

    return df
#-----------------------------------------
def main():
    df = get_df()

    for year in data.l_year:
        for trig in data.l_trig:
            for par in data.l_par:
                df_f = df  [  df.year     == year]
                df_f = df_f[df_f.par_name ==  par]

                ax = None
                for trigger, df_t in df_f.groupby('trig'):
                    ax=df_t.plot(x='brem', y='par_val', yerr='par_err', ax=ax, capsize=4, label=data.d_trigger[trigger])

                if par == 'mu_MC':
                    ax.axhline(y=3097, color='red')

                miny, maxy = data.d_range[par]
                ax.set_ylim(miny, maxy)

                plt_path = f'{data.plot_dir}/{year}_{par}.png'
                data.log.visible(f'Saving to: {plt_path}')

                plt.grid()
                plt.title(f'{data.version}; {year}')
                plt.ylabel(data.d_yname[par])
                plt.xlabel('Bremsstrahlung')
                plt.savefig(plt_path)
                plt.close('all')
#-----------------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to perform comparison between triggeers of q2 smearing factors')
    parser.add_argument('-v', '--version' , type=str, help='Version of scale factor')
    args = parser.parse_args()

    data.version  = args.version
    data.plot_dir = utnr.make_dir_path(f'{data.qsq_dir}/get_q2_tables/fits/{data.version}/comparison_trigger')
#-----------------------------------------
if __name__ == '__main__':
    get_args()
    main()

