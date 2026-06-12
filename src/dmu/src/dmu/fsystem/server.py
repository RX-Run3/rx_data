'''
Module holding Server enum
'''
from enum                  import StrEnum, auto
from pathlib               import Path
from dmu.logging.log_store import LogStore

log = LogStore.add_logger('dmu:server')
# -----------------------------------------
class Server(StrEnum):
    '''
    Class meant to represent server 
    '''
    lxlogin= auto()
    local  = auto()
    lxplus = auto()
    # ----------------------
    @property
    def host(self) -> str:
        '''
        String needed to login, e.g. user@host.ch
        '''
        match self:
            case Server.lxplus:
                return '-p 2224 acampove@localhost'
            case Server.local:
                return '-p 2223 acampove@localhost'
            case Server.lxlogin:
                raise ValueError('Requested IHEP host')
    # ----------------------
    @property
    def data_dir(self) -> Path:
        '''
        Directory where data is located
        '''
        match self:
            case Server.lxplus:
                ana_dir = '/eos/lhcb/wg/RD/RX_run3'
            case Server.local:
                ana_dir = '/run/media/acampove/RX' 
            case Server.lxlogin:
                ana_dir = '/publicfs/ucas/user/campoverde/Data' 

        return Path(ana_dir) / 'Data'
# -----------------------------------------
