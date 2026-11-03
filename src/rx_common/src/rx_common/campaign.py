'''
Module holding the Campaign enum
'''
from enum import StrEnum, auto

# ------------------------------
class Campaign(StrEnum):
    '''
    Class representing data taking campaign, e.g. c1
    '''
    c1_24 = auto()
    c2_24 = auto()
    c3_24 = auto()
    c4_24 = auto()
    # --------------------------------
    @property
    def color(self) -> str:
        '''
        Color, for plotting
        '''
        match self:
            case Campaign.c1_24:
                return 'black'
            case Campaign.c2_24:
                return 'blue'
            case Campaign.c3_24:
                return 'green'
            case Campaign.c4_24:
                return 'red'
    # --------------------------------
    @property
    def name(self) -> str:
        '''
        Name used in plots
        '''
        match self:
            case Campaign.c1_24:
                return 'c1'
            case Campaign.c2_24:
                return 'c2'
            case Campaign.c3_24:
                return 'c3'
            case Campaign.c4_24:
                return 'c4'
    # --------------------------------
    @property
    def runs(self) -> tuple[int,int]:
        '''
        First and last runs in campaign

        Numbers from: https://lhcb-dpa.web.cern.ch/lhcb-dpa/wp1/campaigns/2024/s24c4.html
        '''
        match self:
            case Campaign.c1_24:
                return 295226, 297124
            case Campaign.c2_24:
                return 298626, 301278
            case Campaign.c3_24:
                return 304648, 307544
            case Campaign.c4_24:
                return 307589, 308540
# ------------------------------
