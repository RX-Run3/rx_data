'''
Script used to manage jobs in IHEP
'''

import getpass
import argparse
import subprocess

from typing      import Final
from dataclasses import dataclass
from dmu         import LogStore

log=LogStore.add_logger('rx_selection:jmanager_ihep')

_STATUS_JOB_COLUMN : Final[int] = 5
'''Index of column in Condors printout showing the job status'''

_USER : Final[str] = getpass.getuser() 
'''Username'''

_CONDOR_CMD : Final[list[str]] = ['hep_q', '-u', _USER]
'''Command needed to query user jobs'''
#------------------------------
@dataclass
class Conf:
    '''
    Used to configure job management
    '''
    dry_run   : bool 
    '''If true will stop before running any hep related command'''
    memory    : int
    '''Memory requested'''
    held_jobs : list[str]
    '''List of job IDs associated to held jobs'''
#------------------------------
def _get_args() -> Conf:
    parser = argparse.ArgumentParser(description='Used to perform several operations on held jobs')
    parser.add_argument('-m', '--memory' , type=int, help='Memory, in MB', required=True)
    parser.add_argument('-d', '--dry_run',           help='Testing flag' , action  ='store_true')
    parser.add_argument('-l', '--level'  , type=int, help='Log level'    , choices =[10, 20, 30, 40], default=20)
    args = parser.parse_args()

    conf = Conf(
        memory   = args.memory,
        dry_run  = args.dry_run,
        held_jobs= [])

    log.setLevel(args.level)

    return conf
#------------------------------
def _set_held_jobs(cfg : Conf) -> None:
    output = subprocess.check_output(_CONDOR_CMD, text=True)
    l_line = output.splitlines()

    l_job_id = []
    for line in l_line[1:]:
        l_word = line.split()
        if len(l_word) <= _STATUS_JOB_COLUMN or l_word[_STATUS_JOB_COLUMN] != 'H':
            continue

        l_job_id.append(l_word[0])

    cfg.held_jobs = l_job_id
#------------------------------
def _run_command(cfg : Conf, cmd : str, options : list[str]) -> None:
    if  cfg.dry_run:
        log.info(f'{cmd}, {options}')
        return

    log.debug(f'{cmd}, {options}')
    stat = subprocess.run([cmd] + options, check = False)

    if stat.returncode != 0:
        raise ValueError(f'Process returned exit status: {stat.returncode}')
#------------------------------
def _update_memory(cfg : Conf):
    '''
    Will change jobs memory and release 
    '''
    for job_id in cfg.held_jobs:
        try:
            _run_command(cfg, 'hep_edit'   ,  [job_id, '-m', str(cfg.memory)])
            _run_command(cfg, 'hep_release',  [job_id])
        except Exception as exc:
            raise ValueError(f'Failed to edit memory for: {job_id}') from exc
#------------------------------
def main():
    '''
    Script starts here
    '''
    cfg = _get_args()
    _set_held_jobs(cfg = cfg)

    if not cfg.held_jobs:
        log.warning('No held jobs found')
        return

    _update_memory(cfg = cfg)
#------------------------------
if __name__ == '__main__':
    main()
