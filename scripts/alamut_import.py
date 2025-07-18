from pathlib import Path

import duckdb as db


def alamut_import(in_file: Path, out_file: Path):

    db.sql("INSTALL sqlite")
    db.sql("LOAD sqlite")
    db.sql(f"ATTACH '{in_file}' AS alamut (TYPE sqlite)")
    db.sql("USE alamut")
    db.sql(
        f"COPY (SELECT v.gNomen, vh.* FROM variant v FULL OUTER JOIN variant_history vh ON vh.variant_id = v.variant_id) TO '{out_file}'"
    )
