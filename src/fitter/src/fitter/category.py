'''
Module holding the Category class
'''

import re
import yaml

from pydantic    import BaseModel
from typing      import Final
from functools   import cached_property
from pydantic    import ConfigDict
from dmu         import LogStore
from dmu.stats   import FitResult, Model, zfit
from dmu.stats   import utilities as sut
from rx_common   import Block, Brem, Cuts

zpar = zfit.param.Parameter
zpdf = zfit.pdf.BasePDF
log  = LogStore.add_logger('fitter:category')

_CATEGORY_REGEX : Final[str] = r'brem_([x\d]{3})_b(\d+|all)'
# -----------------------------------
class Category(BaseModel, frozen = True):
    '''
    Class meant to represent a fit category, i.e. a fit for a given
    dataset when splitting in e.g. blocks and/or Brem categories

    Attributes

    name     : Name of category, e.g. brem_001_b1
    pdf      : Zfit PDF associated to category
    sumw     : Yield in MC sample associated to category
    model    : List of model names used for category
    selection: Selection that was used to get category, on top of nominal
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name      : str
    pdf       : zpdf
    sumw      : float
    model     : list[Model]
    selection : dict[Cuts,str]
    # ----------------------
    def __lt__(self, other : 'Category') -> bool:
        '''
        Used for enabling sorting of categories

        Block superseeds Brem
        '''
        same_block = self.block == other.block
        same_brem  = self.brem  == other.brem

        if same_block and same_brem:
            raise ValueError('Found two categories sharing block and brem')

        if same_block:
            return self.brem < other.brem

        return self.block < other.block
    # ----------------------
    @cached_property
    def block(self) -> Block:
        '''
        Returns
        -------------
        Block associated to this category
        '''
        mtch = re.match(_CATEGORY_REGEX, self.name)
        if not mtch:
            raise ValueError(f'Cannot extract block information from {self.name}')

        block_str = mtch.group(2)

        return Block.from_str(block_str)
    # ----------------------
    @cached_property
    def brem(self) -> Brem:
        '''
        Returns
        -------------
        Block associated to this category
        '''
        mtch = re.match(_CATEGORY_REGEX, self.name)
        if not mtch:
            raise ValueError(f'Cannot extract brem information from {self.name}')

        brem_str = mtch.group(1)

        return Brem.from_str(value = brem_str)
    # ----------------------
    def __str__(self) -> str:
        pdfs  = sut.print_pdf(pdf = self.pdf, level = 10)

        value = f'Name: {self.name}\n'
        value+= f'Sumw: {self.sumw:.2f}\n'
        value+= f'Models: {self.model}\n'
        value+= 'Selection:\n'
        value+= yaml.safe_dump(self.selection) + '\n'
        value+= 'PDF:\n'
        value+= '\n'.join(pdfs)

        return value
# -----------------------------------
class FitCategory(Category, frozen = True):
    '''
    Same as Category but with fitting specific
    attributes added

    Attributes
    ----------------
    res: Result of fit, optional
    '''
    res : FitResult
# -----------------------------------
