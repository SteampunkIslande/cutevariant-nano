# Why cutevariant-nano

cutevariant-nano comes from the need for a simple yet flexible tool for exploring parquet data.

It relies on duckdb to build complex queries, with a level of abstraction so that the user doesn't have to know what's going on under the hood.

This software is driven by the idea of separating read-only, heavy data, from read/write intensive user operations that refer to what they find interesting in the read-only database.

# How to install

If you'd like to try the latest (uncompiled) python version, just download this folder, create a virtual environment, and then run `pip install -r requirements.txt` (or `pip install -r requirements-dev.txt` if you are a developer)

# Acknowledgement

Huge thanks to Charlotte Lassaigne (charlotte.lassaigne@aphp.fr) for her help with improving this software.

Column `if(contains(main_table.snpeff_Annotation,'intron_variant'), TRY_CAST (regexp_extract(main_table."snpeff_HGVS.c",'[\+|-](\d+)', 1) AS INT16), '0') AS 'Distance de l exon'` is her work.
