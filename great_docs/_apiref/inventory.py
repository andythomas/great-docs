from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import griffe as gf

from ._walkable import Walkable


@dataclass
class InventoryItem(Walkable):
    """A documented object with a URI pointing to its rendered location"""

    obj: gf.Object | gf.Alias
    name: str = ""
    uri: str | None = None
    dispname: str | None = None


def write_inventory(inv: dict[str, Any], out_name: str) -> None:
    """Write an inventory to a JSON file

    Parameters
    ----------
    inv :
        Inventory data.
    out_name :
        Output file name.
    """
    with open(out_name, "w") as f:
        json.dump(inv, f)


def create_inventory(
    project: str,
    version: str,
    items: list[InventoryItem],
) -> dict[str, Any]:
    """Build the inventory as a dictionary of project, version, count, and items

    Parameters
    ----------
    project :
        Name of the project.
    version :
        Version of the project.
    items :
        Documented objects to include.
    """
    return {
        "project": project,
        "version": version,
        "count": len(items),
        "items": [_create_inventory_item(item) for item in items],
    }


# Sphinx roles have no spaces, so griffe's kind values cannot be used verbatim.
# A PEP 695 alias maps to `py:type` (Sphinx 7.4+); every other kind already
# matches its role name.
_KIND_ROLES = {"type alias": "type"}


def _create_inventory_item(item: InventoryItem, priority: str = "1") -> dict[str, Any]:
    """Build a single inventory entry as a dict"""
    return {
        "name": item.name,
        "domain": "py",
        "role": _KIND_ROLES.get(item.obj.kind.value, item.obj.kind.value),
        "priority": priority,
        "uri": item.uri,
        "dispname": item.dispname or "-",
    }
