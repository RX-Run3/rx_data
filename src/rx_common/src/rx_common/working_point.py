'''
Module holding
'''
from functools     import cached_property, lru_cache
from ROOT          import RDF
from dmu.generic   import hashing
from pydantic      import RootModel, model_validator
from .cuts         import Cut, Cuts

# --------------------------------
class WorkingPoint(RootModel[list[Cut]], frozen = True):
    '''
    Class meant to represent a set of cuts
    '''
    # ----------------
    @property
    def location(self) -> tuple[float,...]:
        '''
        Tuple of floats with the location of working point
        '''
        values = [ elm.val for elm in self.root ]

        return tuple(values)
    # ----------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'WorkingPoint':
        unique_cuts = set(self.root)

        if len(unique_cuts) != self.size:
            raise ValueError(f'Found repeated cuts: {self}')

        return self
    # ----------------
    def __str__(self):
        cuts  = [ str(cut) for cut in self.root ]
        lines = '\n'.join(cuts)

        return f'\n{lines}'
    # ----------------
    @cached_property
    def cuts(self) -> list[Cuts]:
        '''
        List of cuts used for the working point
        '''
        return [ cut.cut for cut in self.root ]
    # ----------------
    def select(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ---------------
        rdf: Dataframe before selection

        Returns
        ---------------
        Dataframe after selection associated to working point
        '''
        for cut in self.root:
            expr = f'{cut.var} > {cut.val}'
            rdf  = rdf.Filter(expr, cut.cut)

        return rdf
    # ----------------
    def __hash__(self) -> int:
        data = self.model_dump()
        hsh  = hashing.hash_object(obj = data, as_int = True)

        return hsh
    # ----------------
    def get_val(self, cut : Cuts) -> float:
        '''
        Parameters
        -------------
        cut: Cut that should be part of working point

        Returns
        -------------
        Value of cut
        '''
        for elm in self.root:
            if elm.cut == cut:
                return elm.val

        raise ValueError(f'No cut found for {cut}')
    # ----------------
    def extend(self, other : 'WorkingPoint') -> 'WorkingPoint':
        '''
        Takes working point, returns working point with extended cuts
        '''
        new_root = self.root + other.root

        return WorkingPoint(root = new_root)
    # ----------------
    def clone(self, values : list[float]) -> 'WorkingPoint':
        '''
        Parameters
        -----------------
        values: List of values of cuts at this WorkingPoint

        Returns
        -----------------
        Copy of current working point with cut values overriden
        '''
        if self.size != len(values):
            raise ValueError(f'Cut values have the wrong size, expected {self.size}, got: {values}')

        new_cuts = [ cut.clone(value = value) for cut, value in zip(self.root, values, strict = True) ]

        return WorkingPoint(root = new_cuts)
    # ----------------
    @classmethod
    @lru_cache
    def empty(cls) -> 'WorkingPoint':
        return cls(root = [])
    # ----------------
    @cached_property
    def size(self) -> int:
        '''
        Number of cuts in working point
        '''
        return len(self.root)
    # ----------------
    @cached_property
    def is_empty(self) -> bool:
        '''
        True if no cuts were found
        '''
        return len(self.root) == 0
    # ----------------
    @cached_property
    def variables(self) -> list[str]:
        '''
        Variables used in working point
        '''
        _variables : list[str] = [ cut.var for cut in self.cuts ]

        return sorted(_variables)
# --------------------------------
