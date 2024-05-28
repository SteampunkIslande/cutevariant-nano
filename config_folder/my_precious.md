
# Get run recurrence of variant:

```sql
SELECT main.chromosome,main.position,main.reference,main.alternate,main.snpeff_Gene_Name,main.uuid,main.sample_name,main.run_name,agg.hom_count,agg.het_count,agg.ref_count,agg.var_count,rec.run_recurr FROM 'genotypes/runs/PPI012.parquet' main JOIN 'aggregates/variants.parquet' agg ON main.variant_hash=agg.variant_hash JOIN ( SELECT variant_hash,COUNT(*) as run_recurr FROM (SELECT DISTINCT(sample_name), variant_hash FROM 'genotypes/runs/PPI012.parquet') GROUP BY variant_hash ) rec ON rec.variant_hash=main.variant_hash"
```

