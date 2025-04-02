import pathlib

import duckdb as db


def check_duckdb_hash_function(tested_file):
    """
    Check that the hash function from duckdb didn't change.
    """
    tested_file = pathlib.Path(tested_file)
    if not tested_file.exists():
        return 1

    l = db.sql(
        f"""SELECT hash(concat_ws('-',chromosome,position,reference,alternate)) AS test, variant_hash FROM '{tested_file}' WHERE test != variant_hash"""
    ).fetchall()
    return 0 if not l else 2


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "tested_file",
        type=str,
        help="The file to test.",
    )
    args = parser.parse_args()
    sys.exit(check_duckdb_hash_function(**vars(args)))
