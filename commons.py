import json
import typing
from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw
import yaml


def yaml_load(file: Path):
    with open(file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def duck_db_literal_string_list(l: typing.Iterable) -> str:
    return "[" + ", ".join(f"'{e}'" for e in l) + "]"


def duck_db_literal_string_tuple(l: typing.Iterable) -> str:
    return duck_db_literal_string_list(l).replace("[", "(").replace("]", ")")


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
    if not user_prefs.parent.exists():
        user_prefs.parent.mkdir(parents=True, exist_ok=True)
    old_prefs = {}
    if user_prefs.exists():
        with open(user_prefs, "r", encoding="utf-8") as f:
            old_prefs = json.load(f)

    old_prefs.update(prefs)

    with open(user_prefs, "w", encoding="utf-8") as f:
        json.dump(old_prefs, f)


def load_user_prefs():
    user_prefs = get_user_prefs_file()
    prefs = {}
    if user_prefs.exists():
        with open(user_prefs, "r", encoding="utf-8") as f:
            prefs = json.load(f)
    return prefs


def table_exists(conn: db.DuckDBPyConnection, table_name: str) -> bool:
    try:
        conn.table(table_name)
        return True
    except db.CatalogException:
        return False


def get_config_folder() -> Path:
    try:
        config_folder = Path(load_user_prefs()["config_folder"])
        return config_folder
    except KeyError:
        qw.QMessageBox.warning(
            None,
            qc.QCoreApplication.tr("Validation"),
            qc.QCoreApplication.tr(
                "Pas de dossier de configuration trouvé, veuillez en choisir un.",
            ),
        )
        config_folder = qw.QFileDialog.getExistingDirectory(
            None,
            qc.QCoreApplication.tr(
                "Pas de dossier de configuration trouvé, veuillez en choisir un."
            ),
        )
        if config_folder:
            save_user_prefs({"config_folder": config_folder})
            return Path(config_folder)
        else:
            # Return a non existent path for sure
            p = Path(".1")
            while p.exists():
                p = p.with_name(p.name + ".1")
            return p
