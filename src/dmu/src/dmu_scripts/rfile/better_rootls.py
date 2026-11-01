'''
Script meant to provide previews of ROOT file and replace
ROOT's rootls
'''
import os
import sys
import uproot

from uproot.behaviors.TTree import TTree
from typing                 import Final
from typing                 import cast

_PRINTABLE_BRANCHES : Final[int] = 10
'''Number of branches to print'''
# ----------------------
def _print_branches(tree : TTree) -> None:
    items    = tree.items()
    items    = items[:_PRINTABLE_BRANCHES]
    branches = [ (branch_name, branch.typename) for branch_name, branch in items ]

    print('    ---------')
    print('    Branches:')
    print('    ---------')
    for branch_name, branch_type in branches:
        print(f'    {branch_name:<40}{branch_type}')
# ----------------------
def _print_tree(tree : TTree, name : str) -> None:
    size_mb = sum(branch.compressed_bytes for branch in tree.values()) / 1024**2
    nbranch = len(tree.keys())

    print(f"Tree: {name}")
    print(f"    entries  : {tree.num_entries}")
    print(f"    branches : {nbranch}")
    print(f"    size [MB]: {size_mb:.1f}")
# ----------------------
def main():
    '''
    Entry point
    '''
    path = sys.argv[1]

    if not os.path.isfile(path):
        print(f'Path not found: {path}')
        return

    with uproot.open(path) as f:
        for name, obj in f.items(filter_classname = 'TTree', cycle = False):
            name = cast(str, name)
            if not isinstance(obj, TTree):
                continue

            _print_tree(tree = obj, name = name)
            _print_branches(tree = obj)
# ----------------------
if __name__ == '__main__':
    main()
