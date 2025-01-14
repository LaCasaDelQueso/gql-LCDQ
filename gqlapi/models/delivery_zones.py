from typing import Dict, Literal, Tuple
import unicodedata
import json
from gqlapi import config

# done: to load production ready delivery zones
with open(
    f"{config.__file__.replace('config.py', '') }models/delivery_zones.json", "r"
) as f:
    delivery_zones = json.load(f)

DZ_IDX: Dict[str, str] = {}
for dz in delivery_zones:
    _ser_dz_name = str(dz["zoneName"]).lower().replace(" ", "_").replace("/", "")
    # normalize without accents
    _ser_dz_name = (
        unicodedata.normalize("NFKD", _ser_dz_name)
        .encode("ASCII", "ignore")
        .decode("utf-8")
    )
    for z in dz["zipCode"]:
        DZ_IDX[z] = _ser_dz_name

# Additional Delivery zones
registered_dzs = {
    "oh6rbfads0q": "scorpion_dzs.json",  # Scorpion
}


def get_delivery_zone(additional_zn: str) -> Tuple[Dict[str, str], Literal['default', 'custom']]:
    # if its not in the registered delivery zones
    if additional_zn not in registered_dzs:
        # return the default delivery zones
        return DZ_IDX, 'default'
    local_dz_file = registered_dzs[additional_zn]
    # read file and return the delivery zones
    with open(
        f"{config.__file__.replace('config.py', '') }models/{local_dz_file}", "r"
    ) as f:
        loc_delivery_zones = json.load(f)
    local_dz_idx = {}
    for dz in loc_delivery_zones:
        _ser_dz_name = str(dz["zoneName"]).lower().replace(" ", "_").replace("/", "")
        # normalize without accents
        _ser_dz_name = (
            unicodedata.normalize("NFKD", _ser_dz_name)
            .encode("ASCII", "ignore")
            .decode("utf-8")
        )
        for z in dz["zipCode"]:
            local_dz_idx[z] = _ser_dz_name
    return local_dz_idx, 'custom'
