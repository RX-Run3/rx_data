#!/usr/bin/env python3

from dmu.text.transformer import transformer as txt_trf

import argparse
import logging

log = logging.getLogger('dmu_scripts:text:transformer')
#---------------------------------
class data:
    txt = None
    out = None
    cfg = None
    lvl = None
#---------------------------------
def get_args():
    parser=argparse.ArgumentParser(description='Will transform a text file following a set of rules')
    parser.add_argument('-i', '--input' , type=str, help='Path to input file' , required=True)
    parser.add_argument('-o', '--output', type=str, help='Path to output file, if not passed, it will be same as input, but with trf before extension')
    parser.add_argument('-c', '--config', type=str, help='Path to config file', required=True)
    parser.add_argument('-l', '--loglvl', type=int, help='Log level'          , default=20, choices=[10, 20, 30, 40])
    args = parser.parse_args()

    data.txt = args.input
    data.out = args.output
    data.cfg = args.config
    data.lvl = args.loglvl
#---------------------------------
def set_logs():
    logging.basicConfig()

    log_tr = logging.getLogger('dmu:text:transformer')

    log_tr.setLevel(data.lvl)
    log.setLevel(data.lvl)
#---------------------------------
def main():
    get_args()
    set_logs()

    trf = txt_trf(txt_path=data.txt, cfg_path=data.cfg)
    trf.save_as(data.out)
#---------------------------------
if __name__ == '__main__':
    main()

