'''
Script intended to overlay variables from different datasets
e.g. different friend tree versions
'''

from rx_common    import Cuts
from dmu.plotting import DsetOverlayConf

class Config(DsetOverlayConf):
    selection: dict[Cuts,   str]


# ----------------------
def main():
    '''
    Entry point
    '''
    
# ----------------------
if __name__ == '__main__':
    main()
