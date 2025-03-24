import json
import typing
from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw
import yaml


def default_prefs():
    return {
        "last_session": str(
            Path(
                qc.QStandardPaths().writableLocation(
                    qc.QStandardPaths.StandardLocation.AppDataLocation
                )
            )
            / "last_session.json"
        ),
    }


def add_action_to_menubar(menubar: qw.QMenuBar, path: str, action: qg.QAction):
    current_menu = menubar
    for menu_name in path.split("/"):
        menu = current_menu.findChild(qw.QMenu, menu_name)
        if not menu:
            menu = current_menu.addMenu(menu_name)
            menu.setObjectName(menu_name)
            current_menu = menu
        else:
            current_menu = menu

    current_menu.addAction(action)


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
    nodes = key.split(".")
    for node in nodes[:-1]:
        if node not in d:
            d[node] = {}
        d = d[node]
    d[nodes[-1]] = value


def get_user_prefs_file():
    return (
        Path(
            qc.QStandardPaths().writableLocation(
                qc.QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        / "config.json"
    ).resolve()
