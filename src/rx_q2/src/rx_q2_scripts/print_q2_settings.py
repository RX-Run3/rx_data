#!/usr/bin/env python3

import argparse
import utils_noroot as utnr

#-----------------------------
class data:
    log    = utnr.getLogger(__name__)
    ijob   = None

    l_trig = ['ETOS', 'GTIS']
    l_dset = ['r1', 'r2p1', '2017', '2018']
    l_brem = ['0', '1', '2']
#-----------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Used to print settings used to run q2 systematics jobs')
    parser.add_argument('-i', '--index', type=int , help='Job index', required=True)
    parser.add_argument('-d', '--dset' , nargs='+', help='Dasets to use'            , default=data.l_dset, choices=data.l_dset + ['all'])
    parser.add_argument('-t', '--trig' , nargs='+', help='Triggers to use'          , default=data.l_trig, choices=data.l_trig + ['all'])
    parser.add_argument('-b', '--brem' , nargs='+', help='Bremsstranlung categories', default=data.l_brem, choices=data.l_brem + ['all'])
    args = parser.parse_args()

    data.ijob   = args.index
    data.l_dset = data.l_dset if args.dset == ['all'] else args.dset
    data.l_trig = data.l_trig if args.trig == ['all'] else args.trig
    data.l_brem = data.l_brem if args.brem == ['all'] else args.brem
#-----------------------------
def main():
    index = 0
    njob  = len(data.l_trig) * len(data.l_dset) * len(data.l_brem)
    for trig in data.l_trig:
        for year in data.l_dset:
            for brem in data.l_brem:
                if index != data.ijob:
                    index+= 1
                    continue

                print(f'TRIG={trig}')
                print(f'YEAR={year}')
                print(f'BREM={brem}')
                print(f'NJOB={njob}')

                return
#-----------------------------
if __name__ == '__main__':
    get_args()
    main()

