'''
Script meant to provide previews of ROOT file and replace
ROOT's rootls
'''
import uproot
import sys

from typing import cast

path = sys.argv[1] 
f = uproot.open(path)

seen = set()
for name, obj in f.items():
    name = cast(str, name)
    if not isinstance(obj, uproot.TTree):
        continue
    base = name.split(";")[0]
    if base in seen:
        continue
    seen.add(base)

    size_mb = sum(branch.compressed_bytes for branch in obj.values()) / 1024**2

    print(f"{base}")
    print(f"    entries  : {obj.num_entries}")
    print(f"    branches : {len(obj.keys())}")
    print(f"    size [MB]: {size_mb:.1f}")
    print()
