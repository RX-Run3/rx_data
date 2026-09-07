'''
Module holding Binning class
'''

from dmu.generic import utilities as gut 
from pydantic    import BaseModel, RootModel
from rx_common   import Cuts
from dmu         import LogStore

log=LogStore.add_logger('hqm:binning')
# -------------------------------------------
class Bins(RootModel[dict[str,tuple[float,float]]], frozen = True):
    '''
    Class representing one bin per variable, e.g. 

    var1 -> bin 1
    var2 -> bin 3
    var3 -> bin 5
    '''
    # ---------------------------------------------
    def __str__(self):
        msg = 70 * '-' + '\n'
        msg+= f'{"Variable":<30}{"Lower":<20}{"Upper":<20}\n'
        msg+= 70 * '-' + '\n'
        for var, (lower, upper) in self.root.items():
            msg += f'{var:<30}{lower:<20g}{upper:<20g}\n'

        return msg
    # ---------------------------------------------
    @property
    def selection(self) -> dict[str,str]:
        '''
        Dictionary with the selection corresponding to the bins object
        inclusive on lower bound and exclusive of upper one
        '''
        sel = dict()
        for var, (lower, upper) in self.root.items():
            sel[var] = f'({var} < {upper}) & ({var} >= {lower})'

        return sel
    # ---------------------------------------------
    @property
    def dir_path(self) -> str:
        '''
        String representing path where output is saved
        '''
        vars = list(self.root)
        vars.sort()

        return '/'.join(vars)
# -------------------------------------------
class Binning(RootModel[dict[str,list[tuple[float,float]]]], frozen = True):
    '''
    Class holding binning for variables 
    '''
    # ---------------------------------------------
    @classmethod
    def load(cls) -> 'Binning':
        '''
        Returns instance of binning, loaded from YAML file
        '''
        data = gut.load_data(package = 'hqm_data', fpath = 'config/binning.yaml')

        return cls(**data)
    # ---------------------------------------------
    def __bins_from_str(self, binning : str) -> dict[str,int]:
        '''
        Parameters
        ------------
        binning: String representing binning, e.g. 'var1-1 var2-3'

        Returns
        ------------
        Dictionary mapping variable name to bin index
        '''
        parts = binning.split()
        bins  = dict() 
        fail  = False

        for part in parts:
            try:
                [var, bin] = part.split('-')
            except Exception as exc:
                raise ValueError(f'Cannot extract variable and bin from: {part}') from exc

            if not bin.isnumeric():
                raise ValueError(f'Bin number is not a number in: {part}')

            if var in bins:
                fail = True
                log.error(f'Variable {var} already found')

            bins[var] = int(bin)

        if fail:
            raise ValueError('Invalid binning')

        return bins
    # ---------------------------------------------
    def from_str(self, binning : str) -> 'Bins':
        '''
        Parameters
        ---------------
        binning: String representing sequence of bins, e.g. 'var1-1 var2-3 var3-5'

        Returns
        ---------------
        Bins object holding sequence of bins 
        First bin is labeled with number 1
        '''
        bins = self.__bins_from_str(binning = binning)
        data = { var : self.root[var][bin - 1] for var, bin in bins.items() }

        return Bins(root = data)
# -------------------------------------------
