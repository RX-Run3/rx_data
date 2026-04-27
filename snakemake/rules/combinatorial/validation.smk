import os

configfile: 'snakemake/configs/combinatorial/validation.yaml'

MASS      = 'B_Mass'
TRIGGER   = 'rk_ee_ss'
ANADIR    = os.environ['ANADIR']
ROOT_PATH = f'{ANADIR}/combinatorial/validation'
# ----------------------
def all_targets(wildcards):
    '''
    Expand all output PNGs across every (q2bin, trigger) combination.
    '''
    targets   = []
    for q2bin, paths in config['output'].items():
        for cutflow in config['cutflow']:
            for path in paths:
                full_path = f'{ROOT_PATH}/{q2bin}/{cutflow}/{path}'
                targets.append(full_path)
    return targets
# ----------------------
rule all:
    input:
        all_targets
rule validate_cmb:
    output:
        f'{ROOT_PATH}/{{q2bin}}/{{cutflow}}/{{model}}/{{png_name}}.png'
    params:
        mass   = MASS,
        trigger= TRIGGER,
    shell:
        '''
        validate_cmb \
            -q {wildcards.q2bin} \
            -M {params.mass} \
            -t {params.trigger} \
            -c {wildcards.cutflow}
        '''
