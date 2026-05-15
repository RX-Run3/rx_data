'''
Snakefile for branch_calculator pipeline.
Runs branch calculations for all kinds/projects/parts,
with mva and smear depending on all other kinds.
'''
import os

_SHELL_BLOCK = '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        branch_calculator                         \
            -k {wildcards.friend}                 \
            -P {wildcards.project}                \
            -v {wildcards.vers}                   \
            -s {params.chunk}                     \
            -p {params.part_idx} {params.n_parts} \
            -g {params.phot_veto}
        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''

def _get_setting(wc, name):
    friend = getattr(wc,  'friend')
    project= getattr(wc, 'project')
    cfg    = config['projects'][project][friend]

    if name == 'photon_veto':
        return cfg.get(name, 'none')

    return cfg[name]

ENV    = 'rx_run3'
HOME   = os.environ['HOME'] 
LOGDIR = os.environ['SMKLOG'] 
ANADIR = os.environ['ANADIR'] 
CHUNK  = config['defaults']['chunk_size']

# ──────────────────────────────────────────────────────────────────────
def sentinels(friend):
    '''Path to the sentinel file that marks a part as done.'''
    paths = []
    for project in config['projects']:
        for val, settings in config['projects'][project].items():
            if val != friend:
                continue

            vers = settings['version']
            parts= settings['parts'  ]
            for part in range(parts):
                path = f'{ANADIR}/tmp/sentinels/friends/{project}/{friend}/{vers}/part_{part:03d}.done'
                paths.append(path)

    return paths
# ──────────────────────────────────────────────────────────────────────
rule all:
    '''Request all sentinel files for every combination.'''
    input:
        sentinels(friend = 'mass'           ) +
        sentinels(friend = 'swp_jpsi_misid' ) +
        sentinels(friend = 'swp_cascade'    ) +
        sentinels(friend = 'brem_track_2'   ) +
        sentinels(friend = 'hop'            ) +
        sentinels(friend = 'mva'            ) +
        sentinels(friend = 'smear'          )
# ── Rules ─────────────────────────────────────────────────────────────────────
rule mva:
    '''Request all sentinel files for every combination.'''
    output:
        done = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}/{{vers}}/part_{{part}}.done'
    wildcard_constraints:
        friend = 'mva',
        vers   = r'v\d+',
    input:
        sentinels(friend = 'hop'         ) +
        sentinels(friend = 'smear'       ) +
        sentinels(friend = 'brem_track_2')
    log: 
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.log',
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    params:
        LOGD      = LOGDIR,
        phot_veto = lambda wc : _get_setting(wc, 'photon_veto'),
        n_parts   = lambda wc : _get_setting(wc,       'parts'),
        part_idx  = lambda wc : int(wc.part),
        chunk     = CHUNK,
        home      = HOME,
        env       = ENV,
    shell: _SHELL_BLOCK

rule smear:
    '''Request all sentinel files for every combination.'''
    output:
        done = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}/{{vers}}/part_{{part}}.done'
    wildcard_constraints:
        friend = 'smear',
        vers   = r'v\d+',
    input:
        sentinels(friend = 'brem_track_2')
    log: 
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.log',
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    params:
        LOGD      = LOGDIR,
        phot_veto = lambda wc : _get_setting(wc, 'photon_veto'),
        n_parts   = lambda wc : _get_setting(wc,       'parts'),
        part_idx  = lambda wc : int(wc.part),
        chunk     = CHUNK,
        home      = HOME,
        env       = ENV,
    shell: _SHELL_BLOCK
rule run_independent:
    '''Run branch_calculator for one independent friend / project / part.'''
    output:
        done = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}/{{vers}}/part_{{part}}.done'
    wildcard_constraints:
        friend = '(mass|swp_jpsi_misid|swp_cascade|brem_track_2|hop)',
        vers   = r'v\d+',
    log: 
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{part}}.log',
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    params:
        LOGD      = LOGDIR,
        phot_veto = lambda wc : _get_setting(wc, 'photon_veto'),
        n_parts   = lambda wc : _get_setting(wc,       'parts'),
        part_idx  = lambda wc : int(wc.part),
        chunk     = CHUNK,
        home      = HOME,
        env       = ENV,
    shell: _SHELL_BLOCK
