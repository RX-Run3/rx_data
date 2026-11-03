'''
Module holding FitMetadata class
'''
import re
import math
import json

from pathlib     import Path
from typing      import Any, Final
from pydantic    import BaseModel
from rx_common   import Trigger, Project, Qsq, WorkingPoint
from rx_common   import Block, Brem, Channel, Component, Cut, Cuts
from dmu         import LogStore
from dmu.generic import hashing
from rx_common   import MVAWp

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
    cmb       : MVAWp
    prc       : MVAWp
    block     : Block
    project   : Project
    channel   : Channel
    q2bin     : Qsq
    brem      : Brem
    stats     : tuple[float,float]
    '''
    Number of entries and uncertainty for dataset that was fitted
    '''
    # -------------------
    def weak_hash(self, exclude : str) -> str:
        '''
        Parameters
        -------------
        exclude: Name of field

        Returns
        -------------
        Hash of object, disregarding `exclude` field.
        I.e. two objects with different `exclude` fields would have
        identical hashes
        '''
        excluded = [exclude, 'stats']

        values = []
        for name, this_value in self:
            if name in excluded:
                continue

            values.append(str(this_value))

        return hashing.hash_object(obj = values)
    # -------------------
    @property
    def signal(self) -> Component:
        '''
        Signal component associated to fit
        '''
        trig = Trigger.get_main_trigger(
            channel = self.channel,
            project = self.project)

        if self.q2bin.is_rare:
            return trig.rare_signal

        if   self.q2bin == Qsq.jpsi:
            return trig.reso_jpsi_signal
        elif self.q2bin == Qsq.psi2:
            return trig.reso_psi2_signal
        else:
            raise ValueError(f'Cannot find resonant signal for {self.q2bin} bin and {trig} trigger')
    # -------------------
    @property
    def wp(self) -> WorkingPoint:
        '''
        MVA working point associated to this fit
        '''
        cmb_cut = Cuts.cmb
        prc_cut = Cuts.prc

        cmb = Cut(cut = cmb_cut, val = self.cmb.lower, var = cmb_cut.var)
        prc = Cut(cut = prc_cut, val = self.prc.lower, var = prc_cut.var)

        return WorkingPoint(root = [cmb, prc])
    # -------------------
    @property
    def fields(self) -> list[tuple[str,Any]]:
        '''
        List of tuples with name and value of fields, excluding stats
        Needed to query based on everything but 'stats'
        '''
        all_fields = type(self).model_fields

        return [ (name, getattr(self, name)) for name in all_fields if name != 'stats' ]
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
        str_1 = f'{self.component:<20}{self.cmb:<15}{self.prc:<15}'
        str_2 = f'{self.block:<5}{self.project:<10}{self.channel:<5}{self.q2bin:<10}{str(self.brem):<10}'

        return f'{str_1}{str_2}'
    # -------------------
    def __str__(self):
        return f'''
        Component       : {self.component}
        Combinatorial WP: {self.cmb}
        Part-reco WP    : {self.prc}
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
        masses : dict[str,list[float]] = json.loads(string)
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
            cmb      = MVAWp.from_str(cmb_wp),
            prc      = MVAWp.from_str(prc_wp),
            project  = Project(mtch.group(4)),
            channel  = Channel(mtch.group(5)),
            q2bin    = Qsq(    mtch.group(6)),
            block    = Block.from_str(value = block),
            brem     = Brem.from_str(value = mtch.group(7)),
            stats    = stats,
        )
# -------------------
