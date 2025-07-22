import os
from pathlib import Path

import duckdb as db
import polars as pl


def add_variant_hash(input_parquet: Path, output_parquet: Path) -> None:
    """
    Adds a 'variant_hash' column to the input Parquet file and saves it to the output Parquet file.
    The 'variant_hash' is duckdb's definition of hash applied to the '-' separated chromosome, position, reference, and alternate string.
    """

    db.sql(
        f"""COPY (SELECT *, hash(concat_ws('-',chromosome,position,reference,alternate)) AS variant_hash FROM '{input_parquet}') TO '{output_parquet.with_suffix(".tmp")}' (FORMAT PARQUET)"""
    )
    os.remove(output_parquet)
    output_parquet.with_suffix(".tmp").rename(output_parquet)


def add_variant_format_column(input_parquet: Path, output_parquet: Path) -> None:

    import pyhgvs2 as hgvs
    from pyfaidx import Fasta

    overwriting = input_parquet == output_parquet

    if overwriting:
        output_parquet = input_parquet.with_suffix(".tmp.parquet")

    genome = Fasta("/reference/ref-hg19/genome/ucsc.hg19.fasta")

    lf = (
        pl.scan_parquet(input_parquet)
        .select(
            [
                "gNomen",
                "assembly",
                "chromosome",
                "created",
                "updated",
                "updated_by",
                "acmg",
                "classification",
                "note",
            ]
        )
        .with_columns(
            pl.concat_str(
                [
                    pl.lit("chr"),
                    pl.col("chromosome").cast(pl.Utf8),
                    pl.lit(":"),
                    pl.col("gNomen"),
                ],
                separator="",
            )
            .map_elements(
                lambda x: "-".join([str(s) for s in hgvs.parse_hgvs_name(x, genome)]),
                return_dtype=pl.Utf8,
            )
            .str.splitn("-", 4)
            .struct.rename_fields(["chromosome", "position", "reference", "alternate"])
            .struct.unnest()
        )
    )
    lf.sink_parquet(output_parquet)
    if overwriting:
        os.remove(input_parquet)
        output_parquet.rename(input_parquet)


def alamut_import(in_file: Path, out_file: Path, assembly: str = "GRCh37") -> None:

    db.sql("INSTALL sqlite")
    db.sql("LOAD sqlite")
    db.sql("SET sqlite_all_varchar=true")
    db.sql(f"ATTACH '{in_file}' AS alamut (TYPE sqlite)")
    db.sql("USE alamut")
    db.sql(
        f"COPY (SELECT v.gNomen,v.Assembly,v.chromosome,v.inserted,v.deleted,TRY_CAST(v.start AS INT) AS start,TRY_CAST(v.end AS INT) AS end, vh.created,vh.updated,vh.updated_by,vh.acmg,vh.classification,vh.note FROM variant v FULL OUTER JOIN variant_history vh ON vh.variant_id = v.variant_id WHERE v.Assembly = '{assembly}') TO '{out_file}'"
    )
    if out_file.suffix == ".parquet":
        add_variant_format_column(out_file, out_file)
        add_variant_hash(out_file, out_file)


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
