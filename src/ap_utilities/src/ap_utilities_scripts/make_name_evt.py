'''
Script meant to invert the evt_name.yaml file
such that the keys are the nicknames and the values are the event types
'''
import argparse
import yaml
import ap_utilities.decays.utilities as aput

from importlib.resources            import files
from ap_utilities.logging.log_store import LogStore

log = LogStore.add_logger('ap_utilities:make_name_evt')
# ------------------------------
def _get_data() -> dict[str,str]:
    cfg_path = files('ap_utilities_data').joinpath('naming/evt_name.yaml')
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf-8') as ifile:
        d_evt_name = yaml.safe_load(ifile)

    return d_evt_name
# ------------------------------
def _invert_dict(d_evt_name : dict[str,str]) -> dict[str,str]:
    d_name_evt = {}
    for evt, name in d_evt_name.items():
        formatted_name             = aput.format_nickname(nickname=name)
        d_name_evt[formatted_name] = evt

    return d_name_evt
# ------------------------------
def _parse_arguments():
    parser = argparse.ArgumentParser(description='Script used to invert evttype/nickname dictionary and save to YAML')
    _      = parser.parse_args()
# ------------------------------
def main():
    '''
    Script starts here
    '''
    _parse_arguments()

    d_evt_name = _get_data()
    d_name_evt = _invert_dict(d_evt_name)

    ofile_path = files('ap_utilities_data').joinpath('naming/name_evt.yaml')
    ofile_path = str(ofile_path)

    log.info(f'Saving to: {ofile_path}')
    with open(ofile_path, 'w', encoding='utf-8') as ofile:
        yaml.safe_dump(d_name_evt, ofile)
# ------------------------------
if __name__ == '__main__':
    main()
