import json
import os

def load_json(fpath: str | os.PathLike, return_str=False, **kwargs) -> dict:
    with open(fpath) as file:
        json_dict = json.load(file, **kwargs)
    if return_str:
        return json.dumps(json_dict)
    else:
        return json_dict
