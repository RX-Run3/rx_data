'''
Module holding FitMetadata class
'''
import re

from pathlib    import Path
from pydantic   import BaseModel
from rx_common  import Block, Brem, Channel, Project, Qsq
from .mva_conf  import MVAWp

#dat_regex = r'(\d{3})_(\d{3})_b(\d)/reso/(rk|rkst)/(mm|ee)/(psi2|jpsi)/data_24/fit/.*/brem_([x,0-9]{3})/parameters.json'
#sim_regex = fr'(\d{{3}})_(\d{{3}})_b(\d)/reso/(rk|rkst)/(mm|ee)/(psi2|jpsi)/{signal}/fit/brem_([x,0-9]{{3}})/brem_[x,0-9]{{3}}_b\d/parameters.json'
#self._regexes  : Final[dict[str,str]]  = {'dat' : dat_regex  , 'sim' : sim_regex  }
# -------------------------------
class FitMetadata(BaseModel):
    '''
    Class meant to store fit information
    '''
    mva_cmb : MVAWp
    mva_prc : MVAWp
    block   : Block
    project : Project
    channel : Channel
    q2bin   : Qsq
    brem    : Brem
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
