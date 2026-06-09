'''
Module holding Server enum
'''
import os
from enum                  import StrEnum, auto
from pathlib               import Path
from dmu.logging.log_store import LogStore

log = LogStore.add_logger('dmu:server')
# -----------------------------------------
class Server(StrEnum):
    '''
    Class meant to represent server 
    '''
    local  = auto()
    lxplus = auto()
    lxlogin= auto()
    # ----------------------
    @property
    def host(self) -> str:
        '''
        String needed to login, e.g. user@host.ch
        '''
        match self:
            case Server.lxlogin:
                return 'campoverde@lxlogin.ihep.ac.cn'
            case Server.lxplus:
                return 'acampove@lxplus.ihep.ac.cn'
            case Server.local:
                user = os.environ['USER']
                return f'{user}@localhost'
    # ----------------------
    @property
    def data_dir(self) -> Path:
        '''
        Directory where data is located
        '''
        match self:
            case Server.lxlogin:
                ana_dir = '/publicfs/ucas/user/campoverde/Data'
            case Server.lxplus:
                ana_dir = '/eos/lhcb/wg/RD/RX_run3'
            case Server.local:
                ana_dir = os.environ['ANADIR']

        return Path(ana_dir) / 'Data'
# -----------------------------------------
