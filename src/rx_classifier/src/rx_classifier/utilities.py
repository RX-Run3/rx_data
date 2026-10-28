'''
Module used to store utility functions
'''
from ROOT                  import RDF
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_classifier:utilities')
#---------------------------------
def add_muon_columns(rdf : RDF.RNode) -> RDF.RNode:
    '''
    Defines columns in dataframe, needed only for muon channel:

    - Columns with brem correction, that exist in electron channel, but in the muon channel are the same as the default ones
    '''

    log.info('Defining muon sample columns')

    l_var = [
            'B_PT',
            'Jpsi_PT',
            'B_DIRA_OWNPV',
            'Jpsi_DIRA_OWNPV',
            'L1_PT',
            'L2_PT',
            'B_M',
            ]

    log.debug(50 * '-')
    log.debug(f'{"Variable":<30}{"Expression"}')
    log.debug(50 * '-')
    for var in l_var:
        # The underscore is needed due to:
        #
        # - ROOT does not allow for branches with periods
        # - Periods are replaced with underscore in CVPredict tool anyway.
        name_2 =              f'{var}_brem_track_2'
        name_1 = f'brem_track_2_{var}_brem_track_2'

        log.debug(f'{name_1:<50}{var}')
        log.debug(f'{name_2:<50}{var}')

        rdf = rdf.Define(name_1, var)
        rdf = rdf.Define(name_2, var)

    return rdf
#---------------------------------
