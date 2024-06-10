
# Get run recurrence of variant:

```sql
SELECT main.chromosome,main.position,main.reference,main.alternate,main.snpeff_Gene_Name,main.sample_name,main.run_name,agg.hom_count,agg.het_count,agg.ref_count,agg.var_count,rec.run_recurr FROM 'genotypes/runs/PPI012.parquet' main JOIN 'aggregates/variants.parquet' agg ON main.variant_hash=agg.variant_hash JOIN ( SELECT variant_hash,COUNT(*) as run_recurr FROM (SELECT DISTINCT(sample_name), variant_hash FROM 'genotypes/runs/PPI012.parquet') GROUP BY variant_hash ) rec ON rec.variant_hash=main.variant_hash"
```

```python
select(fields=[field("chromosome","main_table"),field("position","main_table"),field("reference","main_table"),field("alternate","main_table"),field("snpeff_Gene_Name","main_table"),field("sample_name","main_table"),field("run_name","main_table"),field("hom_count","agg"),field("het_count","agg"),field("ref_count","agg"),field("var_count","agg"),field("run_recurr","rec")],tables=[table("'genotypes/runs/PPI012.parquet'","main_table"),join(val="'aggregates/variants.parquet'",alias="agg",on=filt("AND",filt("LEAF","main_table.variant_hash=agg.variant_hash"))),join(select(fields=["variant_hash","COUNT(*) as run_recurr"]),filt("AND",filt("LEAF","rec.variant_hash=main_table.variant_hash")))])
```