'''
This script tests uses of typehinting with ROOT
'''
from ROOT import RDataFrame, RDF

def test_rdf_type() -> RDF.RNode|None:
    '''
    This method tests using RDF.RNode as return type
    '''
    rdf = RDataFrame(10)
    print('testing')

    return rdf
