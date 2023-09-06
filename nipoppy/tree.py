import json
from pathlib import Path
import argparse

# Globals
dir_tree_json = "tree.json"

def get_paths(k,v):
    subdirs = v["subdirs"]
    path_list = []
    if len(subdirs) > 0:
        for d,_ in subdirs.items():
            subdir_path = f"{k}/{d}"
            path_list.append(subdir_path)
    else:
        path_list.append(k)
                
    return path_list


def run(mr_proc_root, dir_tree_json="tree.json"):
    print("-"*50)
    print(f"Reading {dir_tree_json} to generate list of dir paths")
    path_list = []
    # Generate paths from json
    with open(dir_tree_json, 'r') as f:
        tree = json.load(f)

    for k,v in tree.items():
        path_list += (get_paths(k,v))

    print(f"\nFound {len(path_list)} dir paths")
    # Create dir-tree
    for p in path_list:
        abs_path = f"{mr_proc_root}/{p}"
        Path(abs_path).mkdir(parents=True, exist_ok=True)

    print(f"Finished generating mr_proc_tree under root: {mr_proc_root}")
    print("-"*50)

if __name__ == '__main__':
    HELPTEXT = """
    Script to generate mr_proc directory tree (only upto one subdir level)
    """
    parser = argparse.ArgumentParser(description=HELPTEXT)
    parser.add_argument('--mr_proc_root', type=str, required=True, help='path to mr_proc_root dir')
    parser.add_argument('--dir_tree_json', type=str, default="tree.json", help='path to dir tree')
    args = parser.parse_args()

    mr_proc_root = args.mr_proc_root
    dir_tree_json = args.dir_tree_json

    run(mr_proc_root, dir_tree_json)

