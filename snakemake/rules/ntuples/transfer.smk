import os
from pathlib import Path

SERVER = 'ihep'
DATASET= 'from_ap'
SSHOPT = '-o StrictHostKeyChecking=no -o BatchMode=yes -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o Ciphers=aes128-gcm@openssh.com'

LOCAL_ANADIR   = os.environ['ANADIR']
REMOTE_ANADIR  = config['remote_root'][SERVER]
REMOTE_URL     = config['servers'][SERVER]
RELATIVE_ROOTS = config['paths'][DATASET]
# ── Helpers ───────────────────────────────────────────────────────────────────
def get_local_paths():
    '''
    Returns paths to ROOT files that would exist locally, once copied
    '''
    remote_paths = []
    for relative_root in RELATIVE_ROOTS:
        remote_root  = f'{REMOTE_ANADIR}/{relative_root}'
        remote_paths+= list(Path(remote_root).rglob('*.root'))

    if not remote_paths:
        raise ValueError(f'No paths found in: {remote_root}')

    local_paths = []
    for remote_path in remote_paths:
        remote_string= str(remote_path)
        local_path   = remote_string.replace(REMOTE_ANADIR, LOCAL_ANADIR)
        local_paths.append(local_path)

    return local_paths
# ── Rules ─────────────────────────────────────────────────────────────────────
rule all:
    input:
        get_local_paths()
rule rsync_files:
    '''
    Transfers ROOT files from a server to the local machine
    '''
    output:
        local_path    = f'{LOCAL_ANADIR}/{{relative_path}}'
    params:
        REMOTE_ANADIR = REMOTE_ANADIR,
        LOCAL_ANADIR  = LOCAL_ANADIR,
        SSHOPT        = SSHOPT,
    log:
        os.path.join(LOCAL_ANADIR, 'logs/ntuples/transfer', '{relative_path}.log')
    shell:
        '''
        rsync -av                                                     \
              --partial                                               \
              --progress                                              \
              --stats                                                 \
              -e 'ssh {params.SSHOPT}'                                \
                      {params.REMOTE_ANADIR}/{wildcards.relative_path}\
                      {params.LOCAL_ANADIR}/{wildcards.relative_path} \
              2>&1 | tee {log}
        '''
