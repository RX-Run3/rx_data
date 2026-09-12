'''
Module holding tests for CCbarPDF
'''

from hqm.ccbar_pdf import CCbarPDFMaker

def test_simple():
    '''
    Simplest test
    '''
    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    pdf = ccb.get_pdf(obs = obs)
