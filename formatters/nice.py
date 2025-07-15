import os
from formatter import Formatter

import PySide6.QtGui as qg

import app as ap
from ficon import FIcon

DEFAULT_STYLE = {
    "*": {
        "background": {"from_column": ".backgroundcolor"},
        "italic": {"map": {"NULL": True}},
        "color": {"map": {"NULL": "red"}},
    },
    "VAF": {"color": {"from_column": ".vafcolor"}},
    "Allèle de référence": {
        "color": {
            "map": {"A": "green", "C": "red", "G": "blue", "T": "orange", "N": "gray"}
        },
        "bold": {"constant": True},
    },
    "Annotation": {
        "color": {
            "map": {
                "missense_variant": "#bb96ff",
                "synonymous_variant": "#67eebd",
                "stop_gained": "#ed6d79",
                "stop_lost": "#ed6d79",
                "frameshift_variant": "#ff89b5",
            }
        },
        "bold": {"constant": True},
    },
    "Annotation impact": {
        "color": {
            "map": {
                "HIGH": "#ed6d79",
                "MODERATE": "#ff89b5",
                "LOW": "#67eebd",
                "MODIFIER": "#bb96ff",
            }
        },
        "bold": {
            "map": {"HIGH": True, "MODERATE": True, "LOW": False, "MODIFIER": False}
        },
    },
    "Validé ?": {
        "background": {
            "map": {
                "OUI": "green",
                "NON": "#A1A1A1",
            }
        }
    },
    "Génotype": {
        "icon": {
            "map": {
                "HOM": "0xF0AA5",
                "HET": "0xF0AA1",
                "REF": "0xF0766",
                "UNK": "0xF0625",
            }
        }
    },
}


class NiceFormatter(Formatter):

    DISPLAY_NAME = "Nice formatter"

    def __init__(self, app: "ap.App"):
        config_folder = app.get_config_folder()

        formatter_style_file = app.get_user_prefs().get("formatter_style_file", None)
        if formatter_style_file is None:
            formatter_style_file = "nice_style.json"

        if not os.path.isfile(
            os.path.join(config_folder, "styles", formatter_style_file)
        ):
            # Create styles folder if it does not exist
            if not os.path.exists(os.path.join(config_folder, "styles")):
                os.makedirs(os.path.join(config_folder, "styles"))
            # Create default config file
            with open(
                os.path.join(config_folder, "styles", formatter_style_file), "w"
            ) as f:
                import json

                json.dump(DEFAULT_STYLE, f, indent=4, ensure_ascii=False)

        with open(
            os.path.join(config_folder, "styles", formatter_style_file), "r"
        ) as f:
            import json

            self.style = json.load(f)

    #     self.refresh()

    # def refresh(self):
    #     pass

    def style_for_field(self, field: str, row_dict: dict, value: str, res: dict):
        if field in self.style:
            style = self.style[field]
            if "color" in style:
                color = style["color"]
                if "from_column" in color:
                    column = color["from_column"]
                    if column in row_dict:
                        res["color"] = qg.QColor(row_dict[column])
                elif "map" in color:
                    if value in color["map"]:
                        res["color"] = qg.QColor(color["map"][value])
                elif "constant" in color:
                    res["color"] = qg.QColor(color["constant"])

            if "background" in style:
                background = style["background"]
                if "from_column" in background:
                    column = background["from_column"]
                    if column in row_dict:
                        res["background"] = qg.QColor(row_dict[column])
                elif "map" in background:
                    if value in background["map"]:
                        res["background"] = qg.QColor(background["map"][value])
                elif "constant" in background:
                    res["background"] = qg.QColor(background["constant"])

            if "bold" in style:
                bold = style["bold"]
                if "from_column" in bold:
                    column = bold["from_column"]
                    if column in row_dict:
                        res["bold"] = bool(row_dict[column])
                elif "map" in bold:
                    if value in bold["map"]:
                        res["bold"] = bool(bold["map"][value])
                elif "constant" in bold:
                    res["bold"] = bool(bold["constant"])

            if "italic" in style:
                italic = style["italic"]
                if "from_column" in italic:
                    column = italic["from_column"]
                    if column in row_dict:
                        res["italic"] = bool(row_dict[column])
                elif "map" in italic:
                    if value in italic["map"]:
                        res["italic"] = bool(italic["map"][value])
                elif "constant" in italic:
                    res["italic"] = bool(italic["constant"])

            if "icon" in style:
                icon = style["icon"]
                if "map" in icon:
                    if value in icon["map"]:
                        res["icon"] = FIcon(int(icon["map"][value], 16))

        return res

    def format(self, field: str, value: str, row_dict: dict, option, is_selected):

        res = {"text": str(value)}

        # Apply global styles
        res = self.style_for_field("*", row_dict, value, res)

        # Apply styles based on field
        res = self.style_for_field(field, row_dict, value, res)

        return res
