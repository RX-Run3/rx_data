'''
Module holding 
'''
from functools     import cached_property
from ROOT          import RDF # type: ignore
from dmu.generic   import hashing
from pydantic      import RootModel, ConfigDict
from .cuts         import Cut, Cuts

# --------------------------------
class WorkingPoint(RootModel[list[Cut]]):
    '''
    Class meant to represent a set of cuts
    '''
    model_config = ConfigDict(frozen=True)
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
        vars : list[str] = [ cut.var for cut in self.cuts ]

        return sorted(vars)
# --------------------------------
