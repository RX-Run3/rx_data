'''
Module holding Binning class
'''
import re
import math

from pathlib     import Path
from typing      import Final
from dmu.generic import utilities as gut
from pydantic    import RootModel
from rx_common   import Block
from dmu         import LogStore

log=LogStore.add_logger('hqm:binning')
# string used as key in block cut
_BLOCK_NAME : Final[str] = 'block'

# regular expression needed to extract bin from cut
_REGEX_AND  : Final[str] = r'\((\w+)>=(\d+\.\d+)\)&\((\w+)<(\d+\.\d+)\)'
# -------------------------------------------
class BinConf(RootModel[dict[str,tuple[float,float,int]]], frozen = True):
    '''
    Class representing one bin per variable, e.g.

    var1 -> lower, upper, bin index
    var2 -> lower, upper, bin index
    var3 -> lower, upper, bin index
    '''
    # ---------------------------------------------
    def __str__(self):
        msg = 70 * '-' + '\n'
        msg+= f'{"Variable":<30}{"Lower":<20}{"Upper":<20}\n'
        msg+= 70 * '-' + '\n'
        for var, (lower, upper, _) in self.root.items():
            msg += f'{var:<30}{lower:<20g}{upper:<20g}\n'

        return msg
    # ---------------------------------------------
    def to_str(self) -> str:
        '''
        String representing binning, e.g.

        var1-x var2-y var3-z...

        where varX represents a variable and x,y,z,
        are the bin indexes
        '''
        parts = []
        for var, (_,_,bin) in self.root.items():
            parts.append(f'{var}-{bin}')

        return ' '.join(parts)
    # ---------------------------------------------
    @property
    def block(self) -> Block:
        '''
        Block associated to this bin, if bin does not involve specific block
        will raise ValueError
        '''
        values = self.root.get(_BLOCK_NAME)
        if values is None:
            raise ValueError(f'Cannot extract block for current bin:\n{self}')

        _, _, iblock = values

        return Block(value = iblock)
    # ---------------------------------------------
    @property
    def label(self) -> str:
        '''
        String representing current bin, used for naming PDFs, etc
        '''
        parts = self.__parts()

        return '_'.join(parts)
    # ---------------------------------------------
    @property
    def selection(self) -> dict[str,str]:
        '''
        Dictionary with the selection corresponding to the bins object
        inclusive on lower bound and exclusive of upper one
        '''
        sel = dict()
        for var, (lower, upper, _) in self.root.items():
            sel[var] = f'({var} >= {lower}) & ({var} < {upper})'

        return sel
    # ---------------------------------------------
    @property
    def dir_path(self) -> Path:
        '''
        Path object representing path where output is saved
        '''
        path = '/'.join(self.__parts())

        return Path(path)
    # ---------------------------------------------
    def __parts(self) -> list[str]:
        parts = list()
        for var, (_, _, ibin) in self.root.items():
            parts.append(f'{var}_{ibin:03d}')

        parts.sort()

        return parts
# -------------------------------------------
class BinningConf(RootModel[dict[str,list[tuple[float,float]]]], frozen = True):
    '''
    Class holding binning for variables
    '''
    # ---------------------------------------------
    @classmethod
    def load(cls) -> 'BinningConf':
        '''
        Returns instance of binning, loaded from YAML file
        '''
        data = gut.load_data(package = 'hqm_data', fpath = 'config/binning.yaml')

        return cls(**data)
    # ---------------------------------------------
    def binning_from_sel(self, sel : dict[str,str]) -> str:
        '''
        Parameters
        -------------
        sel: Dictionary mapping variable to cut on with expression

        Returns
        -------------
        Expression holding binning information, e.g. `mva_cmb-3 mva_prc-2`
        '''
        bins : list[str] = []
        for expr in sel.values():
            part = self.__var_bin(expr = expr)
            bins.append(part)

        sorted_bins = sorted(bins)

        return ' '.join(sorted_bins)
    # ---------------------------------------------
    def __var_bin(self, expr : str) -> str:
        '''
        Parameters
        ---------------
        expr: Expression used in cut, e.g. mva_cmb > 0.5 && mva_prc < 1.0

        Returns
        ---------------
        String associated to bin associated to cut
        '''
        expr = expr.replace(' ' ,  '') # Remove spaces to simplify regex
        expr = expr.replace('&&', '&') # Double ampersand used by ROOT
                                       # regex uses single, used by pandas

        mtch = re.match(pattern = _REGEX_AND, string = expr)
        if not mtch:
            raise ValueError(f'Cannot extract information from cut: {expr}')

        v1 = mtch.group(1)
        los= mtch.group(2)
        v2 = mtch.group(3)
        ups= mtch.group(4)

        if v1 != v2:
            raise ValueError(f'Different variables found in expression: {v1}, {v2}')

        if v1 not in self.root:
            raise ValueError(f'Variable {v1} not found in binning scheme')

        lo = float(los)
        up = float(ups)

        if lo >= up:
            raise ValueError(f'Invalid bounds for expression: {expr}')

        ibin = self.__bin_from_bound(lo = lo, up = up, var = v1)

        return f'{v1}-{ibin}'
    # ---------------------------------------------
    def __bin_from_bound(self, lo : float, up : float, var : str) -> int:
        '''
        Parameters
        ----------------
        var  : Variable in which selection is applied
        lo/up: Lower and upper bounds
        '''
        bounds = self.root[var]
        for ibin, (lower, upper) in enumerate(bounds):
            if math.isclose(lower, lo) and math.isclose(upper, up):
                return ibin + 1

        raise ValueError(f'No bin found for: {var} in [{lo:.3g}, {up:.3g}]')
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
    def from_str(self, binning : str) -> 'BinConf':
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
        data = dict()

        for var, bin in bins.items():
            lower, upper = self.root[var][bin - 1]
            data[var]    = lower, upper, bin

        return BinConf(root = data)
# -------------------------------------------
