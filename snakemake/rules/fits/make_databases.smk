
ENV    = 'rx_run3'
HOME   = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR = '/publicfs/ucas/user/campoverde/Data'
LOGDIR = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
# ---------------------
rule all:
    input: [f'{ANADIR}/DB/fitter/{component}/{trigger}/data.root' for component, trigger in config['samples']]
# ---------------------
rule database_making:
    output:
        f'{ANADIR}/DB/fitter/{{component}}/{{trigger}}/data.root',
    log   :
        prc     = f'{LOGDIR}/{{component}}_{{trigger}}.prc',
        err     = f'{LOGDIR}/{{component}}_{{trigger}}.err',
        out     = f'{LOGDIR}/{{component}}_{{trigger}}.out',
        LOG     = f'{LOGDIR}/{{component}}_{{trigger}}.log',
    params:
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
    resources:
        htcondor_request_mem_mb = 6000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        source setup.sh {params.env} {params.home}

        set -e

        rxdata make-database -c {wildcards.component} -t {wildcards.trigger} -d cmb -d prc -d q2 -d mass -d jpsi_misid -d pid_l

        echo "Databases made with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
