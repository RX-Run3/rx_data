'''
Script used to dump metadata stored in ROOT file to YAML file
'''
import json
import argparse
import yaml

from ROOT import TFile
from dmu  import LogStore

log=LogStore.add_logger('rx_data:dump_metadata')
# ------------------------------
class Data:
    '''
    Data class used to store shared data
    '''
    key_name  = 'metadata'
    yaml_path = 'metadata.yaml'
    fpath : str
# ------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to dump YAML file with metadata from ROOT file')
    parser.add_argument('-f', '--fpath' , type=str, help='Path to ROOT file', required=True)
    args = parser.parse_args()

    Data.fpath = args.fpath
# ------------------------------
def main():
    '''
    Starts here
    '''
    _parse_args()

    ifile = TFile.Open(Data.fpath)
    key   = ifile.FindKey(Data.key_name)
    if not key:
        raise ValueError(f'Metadata with name {Data.key_name} not found')

    metadata = key.ReadObj()
    meta_str = metadata.GetString().Data()
    data     = json.loads(meta_str)
    with open(Data.yaml_path, 'w', encoding='utf-8') as ofile:
        yaml.safe_dump(data, ofile, width=float('inf'), sort_keys=False)
# ------------------------------
if __name__ == '__main__':
    main()
