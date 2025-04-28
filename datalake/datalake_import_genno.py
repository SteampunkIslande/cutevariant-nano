import os
import shutil
from pathlib import Path

import duckdb as db
import polars as pl


class DataLake:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "raw").mkdir(parents=True, exist_ok=True)
        (self.path / "genotypes" / "partitions").mkdir(parents=True, exist_ok=True)
        (self.path / "genotypes" / "runs").mkdir(parents=True, exist_ok=True)
        (self.path / "aggregates").mkdir(parents=True, exist_ok=True)
        (self.path / "vcf_extracted").mkdir(parents=True, exist_ok=True)


def weird_fix_parquet(parquet_file: Path):
    """Re-generates parquet file using duckdb standards, fixes uint64 columns saved from polars"""
    db.sql(
        f"COPY (SELECT * FROM '{parquet_file}' ) TO '{parquet_file}.tmp' (FORMAT PARQUET)"
    )
    os.remove(parquet_file)
    os.rename(f"{parquet_file}.tmp", parquet_file)


def nmd_parser(lf: pl.LazyFrame) -> pl.LazyFrame:
    NMD_FIELDS = [
        "nmd_Gene_Name",
        "nmd_Gene_ID",
        "nmd_Number_of_transcripts_in_gene",
        "nmd_Percent_of_transcripts_affected",
    ]
    return (
        lf.explode("info_NMD")
        .with_columns(
            pl.col("info_NMD")
            .str.splitn("|", len(NMD_FIELDS))
            .struct.rename_fields(NMD_FIELDS)
        )
        .unnest("info_NMD")
    )


def lof_parser(lf: pl.LazyFrame) -> pl.LazyFrame:
    LOF_FIELDS = [
        "lof_Gene_Name",
        "lof_Gene_ID",
        "lof_Number_of_transcripts_in_gene",
        "lof_Percent_of_transcripts_affected",
    ]
    return (
        lf.explode("info_LOF")
        .with_columns(
            pl.col("info_LOF")
            .str.splitn("|", len(LOF_FIELDS))
            .struct.rename_fields(LOF_FIELDS)
        )
        .unnest("info_LOF")
    )


def snpEff_parser(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Assuming the column "info_ANN" is of type string list, parse the snpEFF annotation into a struct with appropriate field names.

    Returns:
        pl.Expr: A polars expression of type struct containing the parsed snpEFF annotation
    """
    ANN_FIELDS = [
        "snpeff_Allele",
        "snpeff_Annotation",
        "snpeff_Annotation_Impact",
        "snpeff_Gene_Name",
        "snpeff_Gene_ID",
        "snpeff_Feature_Type",
        "snpeff_Feature_ID",
        "snpeff_Transcript_BioType",
        "snpeff_Rank",
        "snpeff_HGVS.c",
        "snpeff_HGVS.p",
        "snpeff_cDNA.pos/cDNA.length",
        "snpeff_CDS.pos/CDS.length",
        "snpeff_AA.pos/AA.length",
        "snpeff_Distance",
        "snpeff_ERRORS/WARNINGS/INFO",
    ]
    return (
        lf.explode("info_ANN")
        .with_columns(
            pl.col("info_ANN")
            .str.splitn("|", len(ANN_FIELDS))
            .struct.rename_fields(ANN_FIELDS)
        )
        .unnest("info_ANN")
        .filter(pl.col("snpeff_Allele") == pl.col("alternate"))
    )


def preprocess_parquet(input_parquet: Path, output_parquet: Path):
    sample_names = [
        s.replace("_GT", "").replace("format_", "")
        for s in pl.scan_parquet(input_parquet).collect_schema().names()
        if s.endswith("_GT") and s.startswith("format_")
    ]

    db.sql(
        f"""COPY (SELECT *, hash(concat_ws('-',chromosome,position,reference,alternate)) AS variant_hash FROM '{input_parquet}') TO '{output_parquet.with_suffix(".tmp")}' (FORMAT PARQUET)"""
    )

    # Basic data cleaning and transformation, this is considered the raw data we can always go back to
    lf = (
        pl.scan_parquet(output_parquet.with_suffix(".tmp"))
        .with_columns(
            *[
                pl.col(f"format_{sample}_AD")
                .list.get(1, null_on_oob=True)  # Get the alternate allele depth
                .truediv(pl.col(f"format_{sample}_DP"))
                .alias(
                    f"cv_{sample}_AF"
                )  # Calculate allele frequency and prefix it with cv_ for cutevariant
                for sample in sample_names
            ],
        )
        .with_columns(
            *[
                pl.when(pl.col(f"cv_{sample}_AF").is_null())
                .then(-1)  # Unknown genotype
                .when(pl.col(f"cv_{sample}_AF").is_nan())
                .then(-1)  # Unknown genotype
                .when(pl.col(f"cv_{sample}_AF").is_infinite())
                .then(-1)  # Unknown genotype
                .when(pl.col(f"cv_{sample}_AF").ge(0.75))
                .then(2)  # Homozygous alternate
                .when(pl.col(f"cv_{sample}_AF").le(0.25))
                .then(0)  # Homozygous reference
                .otherwise(1)  # Heterozygous
                .alias(
                    f"cv_{sample}_GT"
                )  # Calculate genotype and prefix it with cv_ for cutevariant
                for sample in sample_names
            ]
        )
    )
    lf = snpEff_parser(lf)
    lf = nmd_parser(lf)
    lf = lof_parser(lf)
    lf.sink_parquet(output_parquet)
    os.remove(output_parquet.with_suffix(".tmp"))
    weird_fix_parquet(output_parquet)


def aggregate_variants(incoming_parquet: Path, datalake: DataLake):
    incoming_aggregate_lf = (
        pl.scan_parquet(incoming_parquet)
        .select(
            pl.col("variant_hash"),
            pl.col("chromosome"),
            pl.col("position"),
            pl.col("reference"),
            pl.col("alternate"),
            pl.col("^cv_(.+)_GT$"),
        )
        .unique("variant_hash")
        .with_columns(
            pl.concat_list(pl.col("^cv_(.+)_GT$")).alias(
                "genotypes"
            ),  # Save all genotypes
        )
        .with_columns(
            pl.col("genotypes")
            .list.count_matches(0)
            .alias("ref_count"),  # Count reference genotypes
            pl.col("genotypes")
            .list.count_matches(1)
            .alias("het_count"),  # Count heterozygous genotypes
            pl.col("genotypes")
            .list.count_matches(2)
            .alias("hom_count"),  # Count homozygous genotypes
            pl.col("genotypes")
            .list.len()
            .sub(pl.col("genotypes").list.count_matches(-1))
            .alias("var_count"),  # Count all genotypes except unknowns
        )
        .select(
            "variant_hash",
            "chromosome",
            "position",
            "reference",
            "alternate",
            "hom_count",
            "het_count",
            "ref_count",
            "var_count",
        )
    )

    aggregate_parquet = datalake.path / "aggregates" / "variants.parquet"

    if not os.path.isfile(aggregate_parquet):
        incoming_aggregate_lf.sink_parquet(aggregate_parquet)
        weird_fix_parquet(aggregate_parquet)
    else:
        # Temporary file to store the updated aggregates
        intermediate_aggregates = (
            datalake.path / "aggregates" / "incoming_update.parquet"
        )
        incoming_aggregate_lf.sink_parquet(intermediate_aggregates)
        weird_fix_parquet(intermediate_aggregates)

        new_aggregates = datalake.path / "aggregates" / "new_aggregates.parquet"

        # For each variant in aggregates/variant.parquet, join with incoming parquet on variant_hash, and update zygosities
        db.sql(
            f"""COPY
            (
                SELECT
                coalesce(inc.variant_hash,agg.variant_hash) as variant_hash,
                coalesce(inc.chromosome,agg.chromosome) as chromosome,
                coalesce(inc.position,agg.position) as position,
                coalesce(inc.reference,agg.reference) as reference,
                coalesce(inc.alternate,agg.alternate) as alternate,
                ifnull(inc.hom_count,0) + ifnull(agg.hom_count,0) as hom_count,
                ifnull(inc.het_count,0) + ifnull(agg.het_count,0) as het_count,
                ifnull(inc.ref_count,0) + ifnull(agg.ref_count,0) as ref_count,
                ifnull(inc.var_count,0) + ifnull(agg.var_count,0) as var_count
                FROM '{aggregate_parquet}' agg
                FULL OUTER JOIN '{intermediate_aggregates}' inc
                ON agg.variant_hash = inc.variant_hash
            )
            TO '{new_aggregates}'"""
        )
        # Overwrite the old aggregate file with the new one
        shutil.move(new_aggregates, aggregate_parquet)

        os.remove(intermediate_aggregates)


def split_by_sample(input_parquet: Path, output_parquet: Path, run_name: str):

    sample_names = [
        s.replace("format_", "").replace("_GT", "")
        for s in pl.scan_parquet(input_parquet).collect_schema().names()
        if s.endswith("_GT") and s.startswith("format_")
    ]
    if not sample_names:
        return

    for sample_name in sample_names:

        db.sql(
            f"""COPY
            (
                SELECT
                '{sample_name}' AS sample_name,
                '{run_name}' AS run_name,
                COLUMNS
                (c ->   not(starts_with(c,'format')) AND not(starts_with(c,'cv'))
                ),
                COLUMNS('^format_{sample_name}_(.+)$') AS 'format_\\1',
                COLUMNS('^cv_{sample_name}_(.+)$') AS 'cv_\\1'
                FROM '{input_parquet}' WHERE "cv_{sample_name}_GT" != -1
            )
            TO '{output_parquet}.{sample_name}' (FORMAT PARQUET)"""
        )

    db.sql(
        f"""COPY (SELECT *, hash(concat_ws('-',chromosome,position,reference,alternate,snpeff_Feature_ID,sample_name)) AS validation_hash FROM read_parquet('{output_parquet}.*') ) TO '{output_parquet.with_suffix(".tmp")}' (FORMAT PARQUET)"""
    )
    shutil.move(f"{output_parquet.with_suffix('.tmp')}", output_parquet)

    for sample_name in sample_names:
        os.remove(f"{output_parquet}.{sample_name}")


def save_to_partitions(input_parquet: Path, datalake: DataLake):
    for i in range(256):
        if os.path.isfile(f"{datalake.path}/genotypes/partitions/part{i}.parquet"):
            db.sql(
                f"""
            COPY
            (
                SELECT * FROM read_parquet(['{input_parquet}','{datalake.path}/genotypes/partitions/part{i}.parquet'],union_by_name=True) WHERE variant_hash % 256 = {i}
            )
            TO '{datalake.path}/genotypes/partitions/.part{i}.parquet'
            """
            )
            os.remove(f"{datalake.path}/genotypes/partitions/part{i}.parquet")
            os.rename(
                f"{datalake.path}/genotypes/partitions/.part{i}.parquet",
                f"{datalake.path}/genotypes/partitions/part{i}.parquet",
            )
        else:
            db.sql(
                f"""
            COPY
            (
                SELECT * FROM read_parquet('{input_parquet}') WHERE variant_hash % 256 = {i}
            )
            TO '{datalake.path}/genotypes/partitions/part{i}.parquet'
            """
            )


def init_datalake(datalake_path: Path):
    return DataLake(datalake_path)


def import_parquet(datalake_path: Path, input_parquet: Path):
    datalake = init_datalake(datalake_path)

    run_name = input_parquet.stem.split(".")[0]

    output_parquet = datalake.path / "genotypes" / "runs" / f"{run_name}.parquet"

    preprocessed_parquet = datalake.path / "raw" / input_parquet.name

    # Preprocess the parquet file and save it to the raw folder
    preprocess_parquet(input_parquet, preprocessed_parquet)

    # Split the parquet file by sample
    split_by_sample(
        preprocessed_parquet,
        output_parquet,
        run_name,
    )

    aggregate_variants(preprocessed_parquet, datalake)

    save_to_partitions(output_parquet, datalake)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_parquet", type=Path)
    parser.add_argument("datalake_path", type=Path)

    args = parser.parse_args()
    import_parquet(args.datalake_path, args.input_parquet)
