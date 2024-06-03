import json
import typing
from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc


def duck_db_literal_string_list(l: typing.List) -> str:
    return "[" + ", ".join(f"'{e}'" for e in l) + "]"


def dict_add_value(d: dict, key: str, value: typing.Any):
    """Pythonic way to add a value to an arbitrarly nested dictionary (and without using defaultdict)

    Args:
        d (dict): the dictionnary to add value to
        key (str): a string representing the key to add (may be nested with dots)
        value (Any): the value to add
    """
    if "." in key:
        key, sub_key = key.split(".", 1)
        if key not in d:
            d[key] = {}
        dict_add_value(d[key], sub_key, value)
    else:
        d[key] = value


def get_user_prefs_file():
    return (
        Path(
            qc.QStandardPaths().writableLocation(
                qc.QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        / "config.json"
    ).resolve()


def save_user_prefs(prefs: dict):

    user_prefs = get_user_prefs_file()
    user_prefs.parent.mkdir(parents=True, exist_ok=True)
    old_prefs = {}
    if user_prefs.exists():
        with open(user_prefs, "r") as f:
            old_prefs = json.load(f)

    old_prefs.update(prefs)

    with open(user_prefs, "w") as f:
        json.dump(old_prefs, f)


def load_user_prefs():
    user_prefs = get_user_prefs_file()
    prefs = {}
    if user_prefs.exists():
        with open(user_prefs, "r") as f:
            prefs = json.load(f)
    return prefs


def table_exists(conn: db.DuckDBPyConnection, table_name: str) -> bool:
    try:
        conn.table(table_name)
        return True
    except db.CatalogException as e:
        return False
