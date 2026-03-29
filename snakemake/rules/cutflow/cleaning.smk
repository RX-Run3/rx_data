import os

configfile: '../configs/cutflow/cleaning.yaml'

ANADIR = os.environ['ANADIR']

PLOT_NAMES = [
    '1Trk_mas',
    '2Trk_mas',
    'bmass_brem_corr',
    'bmass_hop',
    'bmass',
    'mass_cascade',
    'mass_jpsi_misid',
    'mva_cmb',
    'q2',
]

QSQ = 'central' 
CFL = 'cleaning'
# --------------------------
def all_outputs():
    outputs = []
    for trigger, samples in config['triggers'].items():
        for sample in samples:
            for plot in PLOT_NAMES:
                path = os.path.join(
                    ANADIR,
                    'plots', 'cutflow', CFL,
                    f'{sample}_{trigger}_{QSQ}',
                    f'{plot}.png',
                )
                outputs.append(path)

    return outputs
# --------------------------
def get_sample_for_output(wildcards):
    '''Infer sample from the output directory name.'''
    dirname = wildcards.dirname
    dirname = dirname.removesuffix(f'_{QSQ}')
    for trigger in config:
        if dirname.endswith(f'_{trigger}'):
            return dirname.removesuffix(f'_{trigger}')

    raise ValueError(f'Cannot infer sample from directory: {wildcards.dirname}')
# --------------------------
def get_trigger_for_output(wildcards):
    '''Infer trigger from the output directory name.'''
    dirname = wildcards.dirname
    dirname = dirname.removesuffix(f'_{QSQ}')
    for trigger in config['triggers']:
        if dirname.endswith(f'_{trigger}'):
            return trigger

    raise ValueError(f'Cannot infer trigger from directory: {wildcards.dirname}')
# --------------------------
rule all:
    input:
        all_outputs()
rule run_cutflow:
    output:
        expand(
            os.path.join(ANADIR, 'plots', 'cutflow', CFL, '{dirname}', '{plot}.png'),
            plot=PLOT_NAMES,
            allow_missing=True,
        )
    params:
        qsq    =QSQ,
        sample =get_sample_for_output,
        trigger=get_trigger_for_output,
        cutflow=CFL,
    shell:
        '''
        cutflow -q {params.qsq} -s {params.sample} -t {params.trigger} -c {params.cutflow}
        '''
