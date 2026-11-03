'''
Module holding PChain class
'''
# pylint: disable=invalid-name
# pylint: disable=missing-function-docstring

from dmu.logging.log_store import LogStore

log=LogStore.add_logger('fitter:pchain')
#----------------------------------
class PChain:
    '''
    Class meant to represent a decay chain
    for a given particle
    '''
    #----------------------------------
    def __init__(
        self,
        pid   : int,
        mid   : int,
        gmid  : int,
        ggmid : int):
        '''
        Takes particle ID for particle and parents
        '''
        self._TID          = pid
        self._MOTHER_TID   = mid
        self._GMOTHER_TID  = gmid
        self._GGMOTHER_TID = ggmid
    #----------------------------------
    @property
    def id(self) -> int:
        return self._TID

    @property
    def mother_id(self) -> int:
        return self._MOTHER_TID

    @property
    def gmother_id(self) -> int:
        return self._GMOTHER_TID

    @property
    def ggmother_id(self) -> int:
        return self._GGMOTHER_TID
    #----------------------------------------------------
    def match_decay(self, l_dec_id : list[int]) -> bool:
        '''
        Parameters
        -----------------
        l_dec_id: List of event numbers for particles in decay

        Return
        -----------------
        True if particles match this decay
        '''
        if len(l_dec_id) == 1:
            return self._TID == abs(l_dec_id[0])

        if len(l_dec_id) == 2:
            return self._TID == abs(l_dec_id[0]) and self._MOTHER_TID == abs(l_dec_id[1])

        if len(l_dec_id) == 3:
            return self._TID == abs(l_dec_id[0]) and self._MOTHER_TID == abs(l_dec_id[1]) and self._GMOTHER_TID == abs(l_dec_id[2])

        if len(l_dec_id) == 4:
            return self._TID == abs(l_dec_id[0]) and self._MOTHER_TID == abs(l_dec_id[1]) and self._GMOTHER_TID == abs(l_dec_id[2]) and self._GGMOTHER_TID == abs(l_dec_id[3])

        return False
    #----------------------------------------------------
    def has_in_chain(self, particle_id : int) -> bool:
        '''
        Parameters
        -----------------
        particle_id: PDG ID of particle

        Returns
        -----------------
        True if this particle is in the current decay chain, mother, grand mother, etc
        '''
        flag = False

        if self._MOTHER_TID   == particle_id:
            flag = True
        if self._GMOTHER_TID  == particle_id:
            flag = True
        if self._GGMOTHER_TID == particle_id:
            flag = True

        return flag
    #----------------------------------------------------
    def match_upstream(self, daughter_id : int, mother_id : int) -> bool:
        '''
        Parameters
        ---------------
        x_id: PDG id of particle

        Returns
        ---------------
        True if decay chain contains particle and daughter with IDs passed
        Also true if daughter is great grand mother in chain
        '''
        flag = False

        if  self._MOTHER_TID   == daughter_id and self._GMOTHER_TID  == mother_id:
            flag = True

        if  self._GMOTHER_TID  == daughter_id and self._GGMOTHER_TID == mother_id:
            flag = True

        if  self._GGMOTHER_TID == daughter_id:
            flag = True

        return flag
    #----------------------------------------------------
    def match_id(self, iD : int) -> bool:
        return self._TID == abs(iD)

    def match_mother(self, iD : int) -> bool:
        return self._MOTHER_TID == abs(iD)

    def match_gmother(self, iD : int) -> bool:
        return self._GMOTHER_TID == abs(iD)

    def match_ggmother(self, iD : int) -> bool:
        return self._GGMOTHER_TID == abs(iD)
#----------------------------------------------------
