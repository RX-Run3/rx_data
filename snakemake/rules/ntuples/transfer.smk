import os

SERVER = 'ihep'
DATASET= 'brem_track_2'
SSHOPT = '-o StrictHostKeyChecking=no -o BatchMode=yes -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o Ciphers=aes128-gcm@openssh.com'

ANADIR = os.environ['ANADIR']
REMOTE = config['servers'][SERVER]
ROOT   = config['root'][SERVER]
PATHS  = config['paths'][DATASET]
# ── Helpers ───────────────────────────────────────────────────────────────────
def all_sync_targets():
    '''Return one sentinel file per (dataset, relative_path) pair.'''
    targets = []
    for rel_path in PATHS:
        sentinel = os.path.join(ANADIR, rel_path, '.rsync_done')
        targets.append(sentinel)

    return targets
# ── Rules ─────────────────────────────────────────────────────────────────────
rule all:
    input:
        all_sync_targets()
rule rsync_directory:
    '''
    Transfer a single remote directory to the local machine via rsync over SSH.
    A hidden sentinel file (.rsync_done) is written on success so Snakemake
    can track completion and skip already-synced directories on re-runs.
    '''
    output:
        sentinel   = os.path.join(ANADIR, '{rel_path}', '.rsync_done')
    params:
        remote_src = lambda wc: f'{REMOTE}:{ROOT}/{wc.rel_path}/',
        local_dst  = lambda wc: os.path.join(ANADIR, wc.rel_path) + '/',
        ssh_opt    = SSHOPT
    log:
        os.path.join(ANADIR, 'logs/ntuples/transfer', '{rel_path}.log')
    shell:
        '''
        mkdir -p {params.local_dst}
        mkdir -p $(dirname {log})

        rsync -av                        \
              --partial                  \
              --progress                 \
              --stats                    \
              -e 'ssh {params.ssh_opt}'  \
                      {params.remote_src}\
                      {params.local_dst} \
              2>&1 | tee {log}

        touch {output.sentinel}
        '''
