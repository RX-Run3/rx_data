'''
Module holding Server enum
'''
import os
from enum                  import StrEnum, auto
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
# -----------------------------------------
