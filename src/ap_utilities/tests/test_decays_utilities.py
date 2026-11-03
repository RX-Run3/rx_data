'''
Module with functions used to test functions in decays/utilities.py
'''
import pytest

from ap_utilities import decay_utilities as aput

# --------------------------------------------------
class Data:
    '''
    Class used to store data needed by tests
    '''

    l_event_type = [
        '10000000',
        '10000010',
        '10000020',
        '10000021',
        '10000022',
        '10000023',
        '10000027',
        '10000030',
        '10002203',
        '10002213',
        '11100001',
        '11100003',
        '11100006',
        ]

    l_new_nick = [
            'Bd_Dmnpipl_eq_DPC',
            'Bd_Dmnpipl_eq_DPC',
            'Bd_Dstplenu_eq_PHSP_TC',
            'Bd_Dstplmunu_eq_PHSP_TC',
            'Bd_Kpimumu_eq_DPC',
            'Bd_Kpimumu_eq_DPC',
            'Bd_Kstee_eq_btosllball05_DPC',
            'Bd_Kstee_eq_btosllball05_DPC',
            'Bd_Kstee_eq_btosllball05_DPC',
            'Bd_Kstee_eq_btosllball05_DPC',
            'Bd_Kstee_eq_DPC',
            'Bd_Kstee_flatq2_eq_DPC_MomCut',
            'Bd_Ksteta_eplemng_eq_Dalitz_DPC',
            ]

    l_lower_case = [
            'data_24_magdown_24c1',
            'data_24_magdown_24c2',
            'data_24_magdown_24c3',
            'data_24_magdown_24c4',
            'data_24_magup_24c1',
            'data_24_magup_24c2',
            'data_24_magup_24c3',
            'data_24_magup_24c4',
            'bu_d0enu_kenu_eq_dpc_ptcut200mev_vismass4gev',
            'bd_denu_kstenu_eq_via_hvm_egdwc',
            'bs_dsenu_phienu_eq_dpc_hvm_egdwc',
            'bd_dmnpipl_eq_dpc',
            'bd_dmnpipl_eq_dpc',
            'bd_dstplenu_eq_phsp_tc',
            'bd_dstplmunu_eq_phsp_tc',
            'bd_kpimumu_eq_dpc',
            'bd_kpimumu_eq_dpc',
            'bu_kee_eq_btosllball05_dpc_spr',
            'bd_kstee_eq_btosllball05_dpc_ss',
            'bd_kstee_eq_btosllball05_dpc',
            'bd_kstee_eq_dpc',
            'bd_kstee_flatq2_eq_dpc_momcut',
            'bd_ksteta_eplemng_eq_dalitz_dpc',
            ]

    l_old_nick = [
            'Bd2DNuKstNuEE',
            'Bd2DPiEE',
            'Bd2DPiMM',
            'Bd2DstNuDPiKPiEE',
            'Bd2DstNuDPiKPiMM',
            'Bd2KPiEE',
            'Bd2KPiMM',
            'Bd2KstEE',
            'Bd2KstEE_central',
            'Bd2KstEE_high',
            'Bd2KstEE_low',
            'Bd2KstEEvNOFLT',
            'Bd2KstEEvPS',
            'Bd2KstEta_EEG',
            ]
# --------------------------------------------------
@pytest.mark.parametrize('event_type', Data.l_event_type)
def test_read_decay_name(event_type : str) -> None:
    '''
    Tests reading of decay name from YAML using event type
    '''
    name = aput.read_decay_name(event_type=event_type)

    print(f'{event_type:<20}{name:<50}')
# --------------------------------------------------
@pytest.mark.parametrize('new_nick', Data.l_new_nick)
def test_read_event_type(new_nick: str) -> None:
    '''
    Tests reading of event type from YAML using new_nick
    '''
    event_type = aput.read_event_type(nickname=new_nick)
    print(event_type)
# --------------------------------------------------
@pytest.mark.parametrize('old_nick', Data.l_old_nick)
def test_new_from_old(old_nick : str) -> None:
    '''
    Will test function returning new nickname style
    from old nickname style
    '''
    old_nick = aput.new_from_old_nick(old_nick)
    print(old_nick)
# --------------------------------------------------
@pytest.mark.parametrize('new_nick', Data.l_new_nick)
def test_old_from_new(new_nick : str) -> None:
    '''
    Will test function returning old nickname style
    from new nickname style
    '''
    old_nick = aput.old_from_new_nick(new_nick)
    print(old_nick)
# --------------------------------------------------
@pytest.mark.parametrize('lower_case', Data.l_lower_case)
def test_name_from_lower_case(lower_case : str) -> None:
    '''
    Will test function that returns original sample name from lower
    case name
    '''
    name = aput.name_from_lower_case(lower_case)
    print(f'{lower_case:<40}{"->":<20}{name:<30}')
