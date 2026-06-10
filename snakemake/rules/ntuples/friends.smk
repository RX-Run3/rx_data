import os
import glob

ENV    = 'rx_run3'
HOME   = config['defaults']['home']
LOGDIR = config['defaults']['smklog']
ANADIR = config['defaults']['anadir']
CHUNK  = config['defaults']['chunk_size']
_MERGE = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}_{{vers}}.merge'
_CALC  = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}_{{vers}}_{{index}}.calc'
_SPLT  = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}_{{vers}}_{{index}}.splt'
# ──────────────────────────────────────────────────────────────────────
def _get_setting(wc, name):
    friend = getattr(wc,  'friend')
    project= getattr(wc, 'project')
    cfg    = config['projects'][project][friend]

    if name == 'photon_veto':
        return cfg.get(name, 'none')

    return cfg[name]
# ──────────────────────────────────────────────────────────────────────
def sentinels(friend):
    paths = []
    for project in config['projects']:
        for val, settings in config['projects'][project].items():
            if val != friend:
                continue

            vers = settings['version']
            path = f'{ANADIR}/tmp/sentinels/friends/{project}/{friend}_{vers}.merge'
            paths.append(path)

    return paths
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
# ───────────────────────────────────────────────────────────────────
rule _merge:
    output:
        done = _MERGE
    input :
        _CALC
    resources:
        htcondor_request_mem_mb  = 5000,
        htcondor_request_disk_mb = 2000,
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.log',
    params:
        LOGD= LOGDIR,
        home= HOME,
        env = ENV,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        merge_friends -p {wildcards.project} -f {wildcards.friend} -v {wildcards.vers}

        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''
# ───────────────────────────────────────────────────────────────────
rule _calculate:
    output:
        done   = _CALC
    resources:
        htcondor_request_mem_mb  = 5000,
        htcondor_request_disk_mb = 2000,
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{index}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{index}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{index}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{index}}.log',
    params:
        phot_veto = lambda wc : _get_setting(wc, 'photon_veto'),
        entries   = lambda wc : _get_setting(wc,     'entries'),
        LOGD      = LOGDIR,
        home      = HOME,
        env       = ENV,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        branch_calculator           \
            -k {wildcards.friend}   \
            -P {wildcards.project}  \
            -v {wildcards.vers}     \
            -i {wildcards.index}    \
            -s {params.entries}     \
            -g {params.phot_veto}
        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''
# ── Rules ─────────────────────────────────────────────────────────────────────
use rule _calculate as calculate_independent with:
    '''Request trees that do not depend on anything'''
    wildcard_constraints:
        friend = '(mass|swp_jpsi_misid|swp_cascade|hop|brem_track_2)',
        vers   = r'v\d+',
    input:
        _SPLT
use rule _calculate as calculate_smear with:
    '''Request mass smearing trees'''
    wildcard_constraints:
        friend = 'smear',
        vers   = r'v\d+',
    input:
        [_SPLT]                           +
        sentinels(friend = 'brem_track_2')
use rule _calculate as calculate_mva with:
    '''Request mva trees'''
    wildcard_constraints:
        friend = 'mva',
        vers   = r'v\d+',
    input:
        [_SPLT]                            +
        sentinels(friend = 'hop'         ) +
        sentinels(friend = 'smear'       ) +
        sentinels(friend = 'brem_track_2')
rule _split:
    output:
        _SPLT
    resources:
        htcondor_request_mem_mb  = 5000,
        htcondor_request_disk_mb = 2000,
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.log',
    params:
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
        entries = lambda wc : _get_setting(wc, 'entries')
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        # {ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}/{{vers}}_{{index}}.splt'
        find_chunks -p {wildcards.project} -e {params.entries} -f {wildcards.friend} -v {wildcards.vers}

        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}
        '''
# ───────────────────────────────────────────────────────────────────
