import app
from filters.filters import FilterItem


class QueryDataPrep(app.AppComponent):

    def __init__(self, app, instance_id):
        self.app = app
        self.instance_id = instance_id

    def load_from_session(self, session):
        pass

    def save_to_session(self):
        pass

    def on_start(self):
        pass

    def widget(self):
        return None

    def get_signal(self, signal_name):
        return None


def build_query_template(data: dict) -> str:
    select_def = data["select"]
    fields = select_def["fields"]
    result = ""
    tables = []
    for i, table_def in enumerate(select_def["tables"]):
        table_def: dict
        if "select" in table_def:
            expr_and_alias = (
                f"({build_query_template(table_def)}) {table_def.get('alias', '')}"
            )
        if "expression" in table_def:
            expr_and_alias = f"{table_def['expression']} {table_def.get('alias', '')}"

        tables.append(
            (
                expr_and_alias,
                table_def["on"] if i != 0 else None,
                table_def["how"] if i != 0 else None,
            )
        )

    result += f"SELECT {', '.join(fields)} FROM {tables[0][0]} "
    for table, on, how in tables[1:]:
        if isinstance(on, dict):
            on = str(FilterItem.from_json(on))
        result += f" {how} JOIN {table} ON {on} "

    if "filter" in select_def:
        filter_def = select_def["filter"]
        filter_str = str(FilterItem.from_json(filter_def))
        if filter_str:
            result += f" WHERE {filter_str} "

    if "group_by" in select_def:
        group_by = select_def["group_by"]
        if isinstance(group_by, list):
            group_by = ",".join(group_by)
        result += f" GROUP BY {group_by} "

    # if "order_by" in select_def:
    #     order_by = select_def["order_by"]

    #     result += " ORDER BY " + ", ".join(
    #         [f"{ob['field']} {ob['order']} " for ob in order_by]
    #     )

    return result
