'''
Module with utilities needed to manipulate ROOT files
'''
from ROOT import TTree, TDirectoryFile

def get_trees_from_file(ifile : TDirectoryFile) -> dict[str,TTree]:
    '''
    Picks up a TFile object
    Returns a dictionary of trees, with the tree location as the key
    Can search recursively within directories
    '''
    if not ifile.InheritsFrom('TDirectoryFile'):
        str_type = str(type(ifile))
        raise ValueError(f'Unrecognized object type {str_type}')

    dir_name = ifile.GetName()

    d_tree={}
    l_key =ifile.GetListOfKeys()

    for key in l_key:
        obj=key.ReadObj()
        if   obj.InheritsFrom('TDirectoryFile'):
            d_tmp = get_trees_from_file(obj)
            d_tree.update(d_tmp)
        elif obj.InheritsFrom('TTree'):
            obj_name = obj.GetName()
            this_key = f'{dir_name}/{obj_name}'

            d_tree[this_key] = obj
        else:
            continue

    return d_tree
