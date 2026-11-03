'''
This module holds tests for BkkInfo class
'''

from typing       import Final
from ap_utilities import BkkInfo
from dmu          import LogStore

SAMPLE_INFO : Final[str] = '''
For BK query: {'ConfigName': 'MC', 'ConfigVersion': '2024', 'ConditionDescription': 'Beam6800GeV-2024.W41.42-MagUp-Nu7.6-25ns-Pythia8', 'ProcessingPass': '/Sim10g/HLT2-2024.W40.42', 'EventType': '12113002', 'FileType': 'HLT2.DST', 'Visible': 'Yes', 'SimulationConditions': 'Beam6800GeV-2024.W41.42-MagUp-Nu7.6-25ns-Pythia8'}
Nb of Files      :  51
Nb of Events     :  413'644
Total size       :  286.865 GB (693.5 kB per evt)
Total size (1024):  267.164 GiB (677.3 kiB per evt)
Luminosity       :  0.000
Size per /pb     :  0.0 GB
'''

log=LogStore.add_logger('ap_utilities:test_bkk_info')
# ----------------------
def test_simple():
    '''
    Simplest test
    '''
    obj = BkkInfo(
        event_type= 123,
        sim_vers  = 'sim_vers',
        block_id  = 'block_id',
        polarity  = 'MagUp',
        ctags     = 'ctags',
        dtags     = 'dtags',
        nu_path   = 'nupath',
        generator = 'generator',
        sample    = 'sample',
        block     = 'block_1',
        stdout    = SAMPLE_INFO)

    log.info('\n' + str(obj.row))
