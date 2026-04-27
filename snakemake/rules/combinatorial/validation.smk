import os

configfile: 'snakemake/configs/combinatorial/validation.yaml'

MASS      = 'B_Mass'
ANADIR    = os.environ['ANADIR']
ROOT_PATH = f'{ANADIR}/combinatorial/validation'
# ----------------------
def all_targets(wildcards):
    '''
    Expand all output PNGs across every (q2bin, trigger) combination.
    '''
    targets = []
    for trigger in config['trigger']:
        for q2bin, paths in config['output'].items():
            for cutflow in config['cutflow']:
                full_path = f'{ROOT_PATH}/{trigger}/{q2bin}/{cutflow}/{paths[0]}'
                targets.append(full_path)

    return targets
# ----------------------
rule all:
    input:
        all_targets
rule validate_cmb:
    output:
        f'{ROOT_PATH}/{{trigger}}/{{q2bin}}/{{cutflow}}/{{model}}/{{png_name}}.png'
    params:
        mass = MASS,
    shell:
        '''
        validate_cmb \
            -M {params.mass} \
            -q {wildcards.q2bin} \
            -t {wildcards.trigger} \
            -c {wildcards.cutflow}
        '''
