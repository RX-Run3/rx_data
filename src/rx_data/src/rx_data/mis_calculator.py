'''
Module with MisCalculator class
'''

from typing    import Final
from ROOT      import RDF
from dmu       import LogStore
from rx_common import Channel, Project, Trigger

log = LogStore.add_logger('rx_data:mis_calculator')
# ----------------------------------------------
class MisCalculator:
    '''
    Class used to add missing variables to ROOT dataframes
    '''
    # -------------
    def __init__(
        self, 
        rdf     : RDF.RNode, 
        trigger : Trigger):
        '''
        Initializer taking dataframe and trigger, the latter is needed to know mass hypotheses of leptons
        '''
        self._rdf    = rdf
        self._trigger= trigger

        self._emass : Final[float] = 0.511 # electron mass
        self._mmass : Final[float] = 105.6 # muon mass
        self._kmass : Final[float] = 493.6 # mass of kaon

        self._lmass = self._get_lepton_mass(trigger)
    # -------------
    def _get_lepton_mass(self, trigger : Trigger) -> float:
        if trigger.channel == Channel.ee: 
            log.debug('Using electron mass hypothesis')
            return self._emass

        if trigger.channel == Channel.mm: 
            log.debug('Using muon mass hypothesis')
            return self._mmass

        raise NotImplementedError(f'Cannot recognize trigger {trigger} as electron or muon')
    # -------------
    def _add_energy(self, rdf : RDF.RNode) -> RDF.RNode:
        l_col = [ name for name in rdf.GetColumnNames() ]

        if 'L1_PE' not in l_col:
            name = 'L1_P'
            rdf  = rdf.Define(f'{name}E', f'TMath::Sqrt({name}X * {name}X + {name}Y * {name}Y + {name}Z * {name}Z + {self._lmass} * {self._lmass})')

        if 'L2_PE' not in l_col:
            name = 'L2_P'
            rdf  = rdf.Define(f'{name}E', f'TMath::Sqrt({name}X * {name}X + {name}Y * {name}Y + {name}Z * {name}Z + {self._lmass} * {self._lmass})')

        if self._trigger.project == Project.rk   and 'H_PE' not in l_col:
            name = 'H_P'
            rdf  = rdf.Define(f'{name}E', f'TMath::Sqrt({name}X * {name}X + {name}Y * {name}Y + {name}Z * {name}Z + {self._kmass} * {self._kmass})')

        if self._trigger.project == Project.rkst and 'H1_PE' not in l_col:
            name = 'H1_P'
            rdf  = rdf.Define(f'{name}E', f'TMath::Sqrt({name}X * {name}X + {name}Y * {name}Y + {name}Z * {name}Z + {self._kmass} * {self._kmass})')

        if self._trigger.project == Project.rkst and 'H2_PE' not in l_col:
            name = 'H2_P'
            rdf  = rdf.Define(f'{name}E', f'TMath::Sqrt({name}X * {name}X + {name}Y * {name}Y + {name}Z * {name}Z + {self._kmass} * {self._kmass})')

        return rdf
    # -------------------------------
    def get_rdf(self) -> RDF.RNode:
        '''
        Returns dataframe after adding variables
        '''
        rdf = self._add_energy(self._rdf)

        return rdf
# ----------------------------------------------
