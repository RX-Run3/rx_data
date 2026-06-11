import os
import glob
from functools import cache
from rx_common import Project
from rx_data   import SampleSplitter
from pathlib   import Path

MAIN_VERSION = 'v1'
ENV    = 'rx_run3'
HOME   = config['defaults']['home']
LOGDIR = config['defaults']['smklog']
ANADIR = config['defaults']['anadir']
_MERGE = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}_{{vers}}.merge'
_CALC  = f'{ANADIR}/tmp/sentinels/friends/{{project}}/{{friend}}_{{vers}}_{{index}}.calc'

CACHED = {
    'rk_10000'    : 178, 
    'rkst_10000'  :  59,
    # -----------
    'rk_100000'   : 1824, 
    'rkst_100000' : 614,
    }
# ──────────────────────────────────────────────────────────────────────
@cache
def _get_parts(project, entries):
    key = f'{project}_{entries}'
    if key in CACHED:
        nbatch = CACHED[key]
        print(f'Found {nbatch} batches from cache for {project} with {entries} entries')
        return nbatch 

    spt = SampleSplitter(
        version = MAIN_VERSION,
        project = project)

    fpath   = Path(f'/tmp/stats_{project}_{MAIN_VERSION}.json')
    files   = spt.run(out_path = fpath)
    batches = files.split(entries = entries)
    nbatch  = batches.size
    print(f'Found {nbatch} batches for {project} with {entries} entries')

    return nbatch
def _get_calc_list(wc):
    dir_name = f'{ANADIR}/tmp/sentinels/friends/{wc.project}'
    entries  = _get_setting(wc, 'entries')
    nparts   = _get_parts(wc.project, entries)

    return [f'{dir_name}/{wc.friend}_{wc.vers}_{index}.calc' for index in range(nparts) ]
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
rule merge:
    output:
        done = _MERGE
    input :
        _get_calc_list
    resources:
        htcondor_request_mem_mb  = 5000,
        htcondor_request_disk_mb = 2000,
    wildcard_constraints:
        vers   = r'v\d+',
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}.log',
    params:
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
        entries = lambda wc : _get_setting(wc, 'entries'),
        fvers   = lambda wc : _get_setting(wc, 'version'),
        mvers   = MAIN_VERSION,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        merge_friends -p {wildcards.project}\
                      -f {wildcards.friend} \
                      -F {params.fvers} \
                      -M {params.mvers}   \
                      -e {params.entries}

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
        mvers     = MAIN_VERSION, 
        fvers     = lambda wc : _get_setting(wc,     'version'),
        LOGD      = LOGDIR,
        home      = HOME,
        env       = ENV,
    shell:
        '''
        (
        source setup.sh {params.env} {params.home}
        echo $_CONDOR_JOB_AD > {log.prc}

        branch_calculator           \
            -g {params.phot_veto}   \
            -k {wildcards.friend}   \
            -P {wildcards.project}  \
            -M {params.mvers}       \
            -F {params.fvers}       \
            -i {wildcards.index}    \
            -e {params.entries}     \
        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}

        mkdir -p $(dirname {output.done})
        touch {output.done}
        '''
# ───────────────────────────────────────────────────────────────────
use rule _calculate as calculate_independent with:
    '''Request trees that do not depend on anything'''
    output:
        done   = _CALC
    wildcard_constraints:
        friend = '(mass|swp_jpsi_misid|swp_cascade|hop|brem_track_2)',
        vers   = r'v\d+',
use rule _calculate as calculate_smear with:
    '''Request mass smearing trees'''
    output:
        done   = _CALC
    wildcard_constraints:
        friend = 'smear',
        vers   = r'v\d+',
    input:
        sentinels(friend = 'brem_track_2')
use rule _calculate as calculate_mva with:
    '''Request mva trees'''
    output:
        done   = _CALC
    wildcard_constraints:
        friend = 'mva',
        vers   = r'v\d+',
    input:
        sentinels(friend = 'hop'         ) +
        sentinels(friend = 'smear'       ) +
        sentinels(friend = 'brem_track_2')
# ───────────────────────────────────────────────────────────────────
