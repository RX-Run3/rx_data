import glob
from setuptools import setup

setup(
        name              = 'rx_hqm2',
        version           = '0.0.1',
        description       = 'Used to build fitting model for high-q2 bin',
        scripts           = glob.glob('scripts/*'),
        long_description  = '', 
        package_dir       = {'' : 'src'},
        package_data      = {'hqm2_data' : ['*/*.json']},
        install_requires  = open('requirements.txt').read().splitlines()
        ) 

