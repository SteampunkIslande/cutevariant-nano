from pathlib import Path

import duckdb as db


def alamut_import(in_file: Path, out_file: Path, assembly: str = "GRCh37") -> None:

    db.sql("INSTALL sqlite")
    db.sql("LOAD sqlite")
    db.sql("SET sqlite_all_varchar=true")
    db.sql(f"ATTACH '{in_file}' AS alamut (TYPE sqlite)")
    db.sql("USE alamut")
    db.sql(
        f"COPY (SELECT v.gNomen,v.Assembly,v.chromosome,v.inserted,v.deleted,TRY_CAST(v.start AS INT) AS start,TRY_CAST(v.end AS INT) AS end, vh.created,vh.updated,vh.updated_by,vh.acmg,vh.classification,vh.note FROM variant v FULL OUTER JOIN variant_history vh ON vh.variant_id = v.variant_id WHERE v.Assembly = '{assembly}') TO '{out_file}'"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import Alamut data into DuckDB.")
    parser.add_argument("in_file", type=Path, help="Input SQLite file path")
    parser.add_argument(
        "out_file", type=Path, help="Output file path (either CSV or Parquet)"
    )
    parser.add_argument(
        "--assembly", type=str, default="GRCh37", help="Genome assembly version"
    )

    args = parser.parse_args()
    alamut_import(args.in_file, args.out_file, args.assembly)
