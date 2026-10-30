import os
import glob
from pathlib     import Path
from functools   import cache
from dmu.generic import Mode

ENV          = config['defaults']['env'      ]
PKGDIR       = config['defaults']['pkgdir'   ]
ANADIR       = config['defaults']['anadir'   ]
HOME         = config['defaults']['home'     ]
MAIN_VERSION = config['defaults']['main_vers']
LOGDIR       = config['defaults']['smklog'   ]

os.environ['USER']   = ENV
os.environ['HOME']   = HOME 
os.environ['ANADIR'] = ANADIR 

from rx_common import Project
from rx_data   import SampleSplitter
# ──────────────────────────────────────────────────────────────────────
@cache
def _get_parts(project, entries):
    fpath = Path(f'{ANADIR}/DB/statistics/v1/{project}.json')
    spt   = SampleSplitter(
        version = MAIN_VERSION,
        project = project)
    files = spt.run(out_path = fpath, mode = Mode.read)

    batches = files.split(entries = entries)
    nbatch  = batches.size
    print(f'Found {nbatch} batches for {project} with {entries} entries')

    return nbatch
def _get_calc_list(wc):
    dir_name = f'{ANADIR}/tmp/sentinels/friends/{wc.project}'
    entries  = _get_setting(wc, 'entries')
    nparts   = _get_parts(wc.project, entries)
    fstem    = wc.fname.removesuffix('.root')
    file_dir = f'{ANADIR}/Data/{wc.project}/{wc.friend}/{wc.version}'

    return [ f'{file_dir}/{fstem}_{index:05d}_pre_merge.root' for index in range(nparts) ]
def _get_setting(wc, name):
    friend = getattr(wc,  'friend')
    project= getattr(wc, 'project')
    cfg    = config['projects'][project][friend]

    if name == 'photon_veto':
        return cfg.get(name, 'none')

    return cfg[name]
@cache
def _get_fnames(project):
    fname_wc = f'{ANADIR}/Data/{project}/main/{MAIN_VERSION}/*.root'
    paths    = glob.glob(fname_wc)

    if not paths:
        raise ValueError(f'No paths found in: {fname_wc}')

    fnames = [ os.path.basename(path) for path in paths ]

    return fnames 
# ──────────────────────────────────────────────────────────────────────
def merge_targets(friend):
    paths = []
    for project in config['projects']:
        settings = config['projects'][project][friend]
        vers     = settings['version']
        dir_path = f'{ANADIR}/Data/{project}/{friend}/{vers}'
        fnames   = _get_fnames(project)
        paths   += [ f'{dir_path}/{fname}' for fname in fnames ]

    return paths
rule all:
    '''Request all merged files for every combination.'''
    input:
        merge_targets(friend = 'mass'          ) +
        merge_targets(friend = 'swp_jpsi_misid') +
        merge_targets(friend = 'swp_cascade'   ) +
        merge_targets(friend = 'brem_track_2'  ) +
        merge_targets(friend = 'hop'           ) +
        merge_targets(friend = 'mva'           ) +
        merge_targets(friend = 'smear'         )
# ───────────────────────────────────────────────────────────────────
rule merge:
    output: f'{ANADIR}/Data/{{project}}/{{friend}}/{{vers}}/{{fname}}'
    input :
        _get_calc_list
    resources:
        htcondor_request_mem_mb  = 4000,
        htcondor_request_disk_mb = 2000,
    wildcard_constraints:
        vers   = r'v\d+',
        project= r'rk|rkst',
        friend = r'mass|swp_jpsi_misid|swp_cascade|brem_track_2|hop|mva|smear',
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fname}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fname}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fname}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fname}}.log',
    params:
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
        pkg     = PKGDIR,
        entries = lambda wc : _get_setting(wc, 'entries'),
        fvers   = lambda wc : _get_setting(wc, 'version'),
        mvers   = MAIN_VERSION,
    shell:
        '''
        (
        export USER={params.env}
        export HOME={params.home}
        set +euo pipefail
        source {params.home}/.bashrc
        set -euo pipefail
        cd {params.pkg}

        echo $_CONDOR_JOB_AD > {log.prc}

        pixi run merge_friends    \
            -p {wildcards.project}\
            -f {wildcards.friend} \
            -F {params.fvers}     \
            -M {params.mvers}     \
            -e {params.entries}

        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}
        '''
# ───────────────────────────────────────────────────────────────────
rule _calculate:
    output   : f'{ANADIR}/Data/{{project}}/{{friend}}/{{vers}}/{{fstem}}_{{index}}_pre_merge.root'
    resources:
        htcondor_request_mem_mb  = 4000,
        htcondor_request_disk_mb = 2000,
    log:
        prc = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fstem}}_{{index}}.prc',
        err = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fstem}}_{{index}}.err',
        out = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fstem}}_{{index}}.out',
        LOG = f'{LOGDIR}/{{project}}_{{friend}}_{{vers}}_{{fstem}}_{{index}}.log',
    params:
        phot_veto = lambda wc : _get_setting(wc, 'photon_veto'),
        entries   = lambda wc : _get_setting(wc,     'entries'),
        mvers     = MAIN_VERSION, 
        fvers     = lambda wc : _get_setting(wc,     'version'),
        LOGD      = LOGDIR,
        home      = HOME,
        env       = ENV,
        pkg       = PKGDIR,
    shell:
        '''
        (
        export USER={params.env}
        export HOME={params.home}
        set +euo pipefail
        source {params.home}/.bashrc
        set -euo pipefail
        cd {params.pkg}

        echo $_CONDOR_JOB_AD > {log.prc}

        pixi run branch_calculator  \
            -g {params.phot_veto}   \
            -k {wildcards.friend}   \
            -p {wildcards.project}  \
            -M {params.mvers}       \
            -F {params.fvers}       \
            -i {wildcards.index}    \
            -e {params.entries}     \
        ) >> {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err}
        ln -s {params.LOGD}/$JOBID.out {log.out}
        ln -s {params.LOGD}/$JOBID.log {log.LOG}
        '''
# ───────────────────────────────────────────────────────────────────
# ───────────────────────────────────────────────────────────────────
use rule _calculate as calculate_independent with:
    '''Request trees that do not depend on any other trees'''
    wildcard_constraints:
        friend = 'mass|swp_jpsi_misid|swp_cascade|brem_track_2|hop',
        vers   = r'v\d+',
        index  = r'\d+',
use rule _calculate as calculate_smear with:
    '''Request trees with smeared masses'''
    input :
        merge_targets(friend = 'brem_track_2')
    wildcard_constraints:
        friend = 'smear',
        vers   = r'v\d+',
        index  = r'\d+',
use rule _calculate as calculate_mva with:
    '''Request trees with mva scores'''
    input :
        merge_targets(friend =        'smear') +
        merge_targets(friend =          'hop') +
        merge_targets(friend = 'brem_track_2')
    wildcard_constraints:
        friend =   'mva',
        vers   = r'v\d+',
        index  = r'\d+',
# ───────────────────────────────────────────────────────────────────
