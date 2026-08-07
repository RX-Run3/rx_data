'''
Module holding FitMetadata class
'''
import re
import math
import json

from pathlib     import Path
from typing      import Final
from pydantic    import BaseModel
from rx_common   import Block, Brem, Channel, Component, Project, Qsq
from dmu         import LogStore
from dmu.generic import hashing
from .mva_conf   import MVAWp

_COMMON   : Final[str] = r'.*\/(\d+-\d+|\d{3})_(\d+-\d+|\d{3})_(all|b\d)\/(?:reso|rare)\/(rk|rkst)\/(mm|ee)\/(low|central|jpsi|psi2|high)'
_DT_REGEX : Final[str] = r'\/_COMP\/fit\/.*\/brem_([x,0-9]{3})\/parameters.json'
_MC_REGEX : Final[str] = r'\/_COMP\/fit\/brem_([x,0-9]{3})\/brem_[x,0-9]{3}(_b\d)?\/parameters.json'

log=LogStore.add_logger('fitter:fit_metadata')

_HASH_STATS : Final[tuple[float,float]] = 1, 1 # Used to calculate hashes, hash should not depend on stats
# -------------------------------
class FitMetadata(BaseModel, frozen = True):
    '''
    Class meant to identify fitted sample 
    '''
    component : Component
    mva_cmb   : MVAWp
    mva_prc   : MVAWp
    block     : Block
    project   : Project
    channel   : Channel
    q2bin     : Qsq
    brem      : Brem
    stats     : tuple[float,float] 
    # -------------------
    def __hash__(self) -> int:
        data = self.__nostats.model_dump()

        return hashing.hash_object(obj = data, as_int = True)
    # -------------------
    @property
    def __nostats(self) -> 'FitMetadata':
        '''
        FitMetadata with statistics field replaced
        with placeholder
        '''
        return self.model_copy(update = {'stats' : _HASH_STATS})
    # -------------------
    @property
    def as_str(self) -> str:
        str_1 = f'{self.component.latex:<30}{self.mva_cmb:<10}{self.mva_prc:<10}'
        str_2 = f'{self.block:<5}{self.project:<10}{self.channel:<5}{self.q2bin:<10}{self.brem:<10}'

        return f'{str_1}{str_2}'
    # -------------------
    def __str__(self):
        return f'''
        Component       : {self.component}
        Combinatorial WP: {self.mva_cmb}
        Part-reco WP    : {self.mva_prc}
        Block           : {self.block}
        Project         : {self.project}
        Channel         : {self.channel}
        Q2 bin          : {self.q2bin}
        Brem            : {self.brem}
        Entries         : {self.stats}
        '''
    # -------------------
    @staticmethod
    def __stats_from_path(path : Path) -> tuple[float,float]:
        '''
        Parameters
        ---------------
        path: Path to parameters.json

        Returns
        ---------------
        Object holding statistics
        '''
        data_path = path.parent / 'data.json' 
        if not data_path.exists():
            raise ValueError(f'Cannot find {data_path}')

        string = data_path.read_text()
        masses = json.loads(string)
        values = masses['Mass']

        value  = len(values)
        error  = math.sqrt(value)

        return value, error
    # -------------------
    @classmethod
    def from_pars_path(cls, path : Path) -> 'FitMetadata':
        '''
        Parameters
        --------------
        path: Path to parameters.json, i.e. file with fit parameters

        Returns
        --------------
        Object holding fit metadata
        '''
        metadata_path = path.parent / 'metadata.json'
        if metadata_path.exists():
            json_string = metadata_path.read_text()
            return cls.model_validate_json(json_string)

        component = Component.from_path(path = path)

        if component.is_mc:
            regex = f'{_COMMON}{_MC_REGEX}'
        else:
            regex = f'{_COMMON}{_DT_REGEX}'

        regex = regex.replace('_COMP', component)
        mtch  = re.match(regex, str(path))
        if not mtch:
            log.error(f'Regex: {regex}')
            message = f'''
            Path does not conform to pattern

            Path   : {path}
            Pattern: {regex}
            '''
            raise ValueError(message)

        cmb_wp = mtch.group(1)
        prc_wp = mtch.group(2)
        block  = mtch.group(3).removeprefix('b') # b3 -> 3
        stats  = cls.__stats_from_path(path = path)

        return cls(
            component= component,
            mva_cmb  = MVAWp.from_label(cmb_wp),
            mva_prc  = MVAWp.from_label(prc_wp),
            project  = Project(mtch.group(4)),
            channel  = Channel(mtch.group(5)),
            q2bin    = Qsq(    mtch.group(6)),
            block    = Block.from_str(value = block),
            brem     = Brem.from_str(value = mtch.group(7)),
            stats    = stats,
        )
# -------------------
