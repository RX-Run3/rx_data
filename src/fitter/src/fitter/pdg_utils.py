'''
Module with functions intended to interface with the PDG API
'''
from dmu   import LogStore

log=LogStore.add_logger('fitter:pdg_utils')
#-------------------------------------------------------
def get_bf(decay : str) -> float:
    '''
    Returns branching fraction for a given decay
    '''
    match decay:
        case 'B+ --> J/psi(1S) K+':
            return 1.019e-3 # https://pdglive.lbl.gov/Particle.action?init=0&node=S041&home=MXXX045
        case 'B0 --> J/psi(1S) K*(892)0':
            return 1.27e-3  # https://pdglive.lbl.gov/Particle.action?init=0&node=S042&home=MXXX045
        case 'B_s()0 --> J/psi(1S) phi':
            return 1.01e-3  # https://pdglive.lbl.gov/Particle.action?init=0&node=S086&home=MXXX046
        case _:
            raise ValueError(f'Cannot find branching fraction for: {decay}')
#-------------------------------------------------------
