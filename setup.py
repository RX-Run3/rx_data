import glob
from setuptools import setup

#-------------------------------------------------
def get_data_files():
    l_json  = list()
    l_json += ['tfunc/int/*/psi2_high_psi2.json']
    l_json += ['ratios/int/*/parameters.json']
    l_json += ['fits/int/*/psi2_ETOS_high/pars.json']
    l_json += ['data/int/*/high_psi2_ETOS/B_M_*.json']
    l_json += ['data/int/*/high_bdks_ETOS/B_M_*.json']
    l_json += ['data/int/*/high_bpks_ETOS/B_M_*.json']
    l_json += ['data/int/*/high_bsph_ETOS/B_M_*.json']
    l_json += ['data/int/*/psi2_data_MTOS/B_M_*.json']
    l_json += ['config/*.toml']

    return l_json
#-------------------------------------------------
setup(
        name              = 'rx_hqm2',
        version           = '0.0.1',
        description       = 'Used to build fitting model for high-q2 bin',
        scripts           = glob.glob('scripts/*'),
        long_description  = '', 
        package_dir       = {'' : 'src'},
        packages          = ['hqm2', 'hqm2_data'],
        package_data      = {'hqm2_data' : get_data_files() },
        install_requires  = open('requirements.txt').read().splitlines()
        ) 

