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
paths = []
for qsq in qsq_bin:
    for cmb in mva_cmb:
        for prc in mva_prc:
            for prj in project:
                for chn in channel:
                    paths += [
                        f'{out_path}/{group_name}/{cmb}_{prc}_all/{mode}/{prj}/{chn}/{qsq}/data_24/fit/brem_xx1_brem_xx2/brem_xx1/fit_linear.png',
                        f'{out_path}/{group_name}/{cmb}_{prc}_all/{mode}/{prj}/{chn}/{qsq}/data_24/fit/brem_xx1_brem_xx2/brem_xx2/fit_linear.png',
                        f'{out_path}/{group_name}/{cmb}_{prc}_all/{mode}/{prj}/{chn}/{qsq}/data_24/fit/brem_xx1_brem_xx2/both_brem/fit_linear.png',
                        ]
# ---------------------------------------
rule all:
    input : paths
# ---------------------
rule fits:
    output:
         f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/{{prj}}/{{chn}}/{{qsq}}/data_24/fit/brem_xx1_brem_xx2/brem_xx1/fit_linear.png',
         f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/{{prj}}/{{chn}}/{{qsq}}/data_24/fit/brem_xx1_brem_xx2/brem_xx2/fit_linear.png',
         f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/{{prj}}/{{chn}}/{{qsq}}/data_24/fit/brem_xx1_brem_xx2/both_brem/fit_linear.png',
    log: f'{out_path}/{group_name}/{{cmb}}_{{prc}}_all/{{mode}}/logs/{{prj}}_{{chn}}_{{qsq}}.log'
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
