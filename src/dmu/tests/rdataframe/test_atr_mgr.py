'''
Module with tests for AtrMgr class
'''

from ROOT                   import RDataFrame
from dmu.rdataframe.atr_mgr import AtrMgr

#--------------------------------
def test_attach():
    '''
    Will test picking up of attached attributes
    '''
    rdf         = RDataFrame(20)
    rdf.name    = 'dataframe_simple'
    rdf.entries = 20
    rdf.l_data  = [1, 2, 3]

    AtrMgr(rdf)
#--------------------------------
def test_dump():
    '''
    Will test dumping attributes to JSON
    '''
    rdf         = RDataFrame(20)
    rdf.name    = 'dataframe_simple'
    rdf.entries = 20
    rdf.l_data  = [1, 2, 3]

    obj = AtrMgr(rdf)
    obj.to_json('/tmp/atr_mgr/test_dump/data.json', exists_ok=True)
#--------------------------------
