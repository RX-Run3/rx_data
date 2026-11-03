#!/usr/bin/env python3

import os
import glob
import argparse
import utils_noroot as utnr

from logzero import logger as log

#-------------------
class data:
    vers   = None
    qsqdir = os.environ['QSQSYS']
#-------------------
def res_to_dpar(res):
    d_par = { name : [d_val['value'], 0.5 * (d_val['errors']['upper'] - d_val['errors']['lower']) ] for name, d_val in res.params.items() }

    return d_par
#-------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to remake JSON files with fit parameters information from pickled result objects')
    parser.add_argument('-v', '--vers' , type =str, help='Versions of tables', required=True)
    args = parser.parse_args()

    data.vers     = args.vers
#-------------------
def make_json():
    pickle_wc = f'{data.qsqdir}/get_q2_tables/fits/{data.vers}/*.pkl'

    l_pickle_path = glob.glob(pickle_wc)

    for pickle_path in l_pickle_path:
        json_path = pickle_path.replace('.pkl', '.json')
        obj   = utnr.load_pickle(pickle_path)
        d_par = res_to_dpar(obj)
        utnr.dump_json(d_par, json_path)
        log.info(f'Saving to: {json_path}')
#-------------------
def main():
    get_args()

    make_json()
#-------------------
if __name__ == '__main__':
    main()

