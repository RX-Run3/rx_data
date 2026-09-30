# ---------------------
def _index_from_cut(cut):
    index_str = cut.split('_')[-1]

    return int(index_str)
# ---------------------
def _get_binning(wc):
    blk = _index_from_cut(wc.blk)
    cmb = _index_from_cut(wc.cmb)
    prc = _index_from_cut(wc.prc)

    return f'block-{blk} mva_cmb-{cmb} mva_prc-{prc}'
# ---------------------
ENV    = 'rx_run3'
HOME   = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR = '/publicfs/ucas/user/campoverde/Data'
LOGDIR = '/publicfs/ucas/user/campoverde/Jobs/snakemake'
BLK    = [ f'block_{blk:03}'   for blk in range(1,  9) ]
CMB    = [ f'mva_cmb_{cmb:03}' for cmb in range(1,  9) ]
PRC    = [ f'mva_prc_{prc:03}' for prc in range(1, 11) ]
# ---------------------
rule all:
    input:
        expand(f'{ANADIR}/DB/hqm/ratios/latest/{{blk}}/{{cmb}}/{{prc}}/rk/parameters.json',
            blk = BLK,
            cmb = CMB,
            prc = PRC)
# ---------------------
rule hqm:
    output:
        f'{ANADIR}/DB/hqm/ratios/latest/{{blk}}/{{cmb}}/{{prc}}/rk/parameters.json',
    log   :
        prc     = f'{LOGDIR}/{{cmb}}_{{prc}}_{{blk}}.prc',
        err     = f'{LOGDIR}/{{cmb}}_{{prc}}_{{blk}}.err',
        out     = f'{LOGDIR}/{{cmb}}_{{prc}}_{{blk}}.out',
        LOG     = f'{LOGDIR}/{{cmb}}_{{prc}}_{{blk}}.log',
    params:
        LOGD    = LOGDIR,
        home    = HOME,
        env     = ENV,
        binning = lambda wc : _get_binning(wc)
    resources:
        htcondor_request_mem_mb = 4000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        (
        source setup.sh {params.env} {params.home}

        set -e

        hqm run-fits   -b "{params.binning}"
        hqm run-trfc   -b "{params.binning}"
        hqm run-prec   -b "{params.binning}"
        hqm run-ratios -b "{params.binning}"
        hqm run-ccbar  -b "{params.binning}"

        echo "Templates made with status: $?"
        ) > {log.prc} 2>&1

        JOBID=$(grep -m1 '^ClusterId' $_CONDOR_JOB_AD | awk '{{print $3}}')
        ln -s {params.LOGD}/$JOBID.err {log.err} || true
        ln -s {params.LOGD}/$JOBID.out {log.out} || true
        ln -s {params.LOGD}/$JOBID.log {log.LOG} || true
        '''
