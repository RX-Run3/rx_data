import os

mva_cmb  = config['mva_cmb']
mva_prc  = config['mva_prc']
qsq_bin  = config['qsq_bin']
project  = config['project']
channel  = config['channel']
# -------------
ENV       = 'rx_run3'
HOME      = '/afs/ihep.ac.cn/users/c/campoverde'
ANADIR    = '/publicfs/ucas/user/campoverde/Data'
out_path  = f'{ANADIR}/fits/data'
group_name= 'rare'
mode      = 'rare'
# ---------------------------------------
def _brem_from_chan(chn):
    if   chn == 'ee':
        brem = 'brem_x12'
    elif chn == 'mm':
        brem = 'brem_xx0'
    else:
        raise ValueError(f'Invalid channel: {chn}')

    return brem
# ---------------------------------------
paths = []
for qsq in qsq_bin:
    for cmb in mva_cmb:
        for prc in mva_prc:
            for prj in project:
                for chn in channel:
                    brem = _brem_from_chan(chn = chn)
                    path = f'{out_path}/{group_name}/{cmb}_{prc}_all/{mode}/{prj}/{chn}/{qsq}/data_24/fit/{brem}/{brem}/fit_linear.png'

                    paths.append(path)
# ---------------------------------------
rule all:
    input : paths
# ---------------------
rule fits:
    output: f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/{{prj}}/{{chn}}/{{qsq}}/data_24/fit/{{brem}}/{{brem}}/fit_linear.png'
    log:    f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/logs/{{prj}}_{{chn}}_{{qsq}}_{{brem}}.log',
    params:
        group_name = group_name,
        home       = HOME,
        env        = ENV,
    resources:
        htcondor_request_mem_mb = 6000,
        htcondor_request_disk_mb= 2000,
    shell :
        '''
        source setup.sh {params.env} {params.home} 

        CMB_WP=$(rxfitter wp-translator -w {wildcards.cmb})
        PRC_WP=$(rxfitter wp-translator -w {wildcards.prc})
        fit_rx_rare \
                    -b -1              \
                    -g {params.group_name}   \
                    -c {wildcards.mode}/{wildcards.prj}/{wildcards.chn}\
                    -q {wildcards.qsq} \
                    -C $CMB_WP         \
                    -P $PRC_WP         \
                    > {log} 2>&1        \
                    || true

        rxfitter make-dummy-plot -p {output} -t {wildcards.cmb}_{wildcards.prc}
        '''
# ---------------------
