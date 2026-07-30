'''
Module holding 
'''
from functools     import cached_property
from ROOT          import RDF # type: ignore
from dmu.generic   import hashing
from pydantic      import RootModel, ConfigDict
from .cuts         import Cut

# --------------------------------
class WorkingPoint(RootModel[list[Cut]]):
    '''
    Class meant to represent a set of cuts
    '''
    model_config = ConfigDict(frozen=True)
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
    @cached_property
    def variables(self) -> list[str]:
        '''
        Variables used in working point
        '''
        vars : list[str] = []
        for elm in self.root: 
            vars.append(elm.var)

        return sorted(vars)

