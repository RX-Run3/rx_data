#!/usr/bin/env python3

import re
import os
import argparse
import pandas       as pnd
import utils_noroot as utnr

from importlib.resources import files
from logzero             import logger as log

#-----------------------------------------------------------
class data:
    l_year = ['2011', '2012', '2015', '2016', '2017', '2018']
    cal_dir= os.environ['CALDIR']
#-----------------------------------------------------------
def get_data(content):
    content= content.replace(' ', '')
    rgx    = r'(-?\d+\.\d+)±(\d+\.\d+)'
    mch    = re.match(rgx, content)

    if not mch:
        log.error(f'Cannot match {content} with {rgx}')
        raise

    val=mch.group(1)
    err=mch.group(2)

    return [float(val), float(err)]
#-----------------------------------------------------------
def preprocess_rk_df(df):
    log.warning('Adding fake mu_MC column to RK table')
    df['mu_MC 0 gamma'] = '3070.0 ± 0.0'
    df['mu_MC 1 gamma'] = '3070.0 ± 0.0'
    df['mu_MC 2 gamma'] = '3070.0 ± 0.0'

    l_df = []
    for trig in ['eTOS', 'TIS']:
        df_o = df.filter(like = trig, axis=0)
        df_o = df_o.rename(index  =lambda name: name.replace(f'_{trig}', ''))

        trig_name = {'eTOS' : 'ETOS', 'TIS' : 'GTIS'}[trig]
        df_o = df_o.rename(columns=lambda name: f'{trig_name} {name}')
        l_df.append(df_o)

    df = pnd.concat(l_df, axis=1)
    df = df.T

    df['2011'] = df.r1p0
    df['2012'] = df.r1p0
    df['2015'] = df.r2p1
    df['2016'] = df.r2p1

    df = df.drop(columns=['r1p0', 'r2p1'])
    df = df.T
    df = df.sort_index()

    return df
#-----------------------------------------------------------
def make_json(version, filename):
    csv_path    = files('q2_data').joinpath(filename)
    df_a        = pnd.read_csv(csv_path)

    if version == 'vk.nom':
        df_a = preprocess_rk_df(df_a)

    df_a.index  = data.l_year
    df_r        = df_a.applymap(get_data)
    df_t        = df_r.transpose()
    if version != 'vk.nom':
        df_i    = df_t.rename(index=lambda name: name.replace('ETOS', 'GTIS'))
        df_b    = pnd.concat([df_t, df_i])
    else:
        df_b    = df_t

    for year in data.l_year:
        df_y   = df_b[year]
        d_data = df_y.to_dict()
        json_path = f'{data.cal_dir}/qsq/{version}/{year}.json'
        log.info(f'Saving to: {json_path}')
        utnr.dump_json(d_data, json_path)
#-----------------------------------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to make v0 q2 parameters from RX table, already in CSV format')
    args = parser.parse_args()
#-----------------------------------------------------------
if __name__ == '__main__':
    get_args()
    make_json('vk.nom', 'rk_kp_q2_pars.csv')
    make_json('vp.nom', 'rx_kp_q2_pars.csv')
    make_json('vs.nom', 'rx_ks_q2_pars.csv')

