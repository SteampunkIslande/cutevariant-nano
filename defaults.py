styles = {
    "nice_style": {
        "*": {
            "background": {"from_column": ".backgroundcolor"},
            "italic": {"map": {"NULL": True}},
            "color": {"map": {"NULL": "red"}},
        },
        "VAF": {"color": {"from_column": ".vafcolor"}},
        "Allèle de référence": {
            "color": {
                "map": {
                    "A": "green",
                    "C": "red",
                    "G": "blue",
                    "T": "orange",
                    "N": "gray",
                }
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
        "Validé ?": {"background": {"map": {"OUI": "green", "NON": "#A1A1A1"}}},
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
}

validation_methods = {
    "validation_immuno": {
        "genes_list": {
            "DLBCL": ["TP53", "CD79B"],
            "Lymphome B": ["TP53", "CD79B", "MYD88", "CD79A", "CARD11"],
        },
        "default": {
            "title": "VAF en rouge + Background color différent de noir",
            "description": "Trié par chromosome",
            "query": {
                "select": {
                    "fields": [
                        '42 AS ".validation_hash"',
                        "'#'||\"Background color\" AS '.backgroundcolor'",
                        "'#'||\"VAF color\" as '.vafcolor'",
                        '"Sample_id"',
                        '"PREDICTED"',
                        '"Project.recurrence"',
                        '"Project.recurrence.DENOM"',
                        '"Analysis_recurrence.N"',
                        '"Analysis.recurrence.DENOM"',
                        '"Glims"',
                        '"Exon.rank"',
                        '"Gene.symbol"',
                        '"Chrom"',
                        '"Position"',
                        '"N.Ref"',
                        '"N.Alt"',
                        '"VAF"',
                        '"Variant.effect"',
                        '"hgvs.p"',
                        '"Depth"',
                        '"NbrReadRef"',
                        '"NbrReadAlt"',
                        '"NbrReadAlt.Pos"',
                        '"NbrReadAlt.Neg"',
                        '"Feature.id"',
                        '"hgvs.c"',
                        '"dbsnp.rs.id"',
                        '"Cosmic.noncoding.id"',
                        '"Cosmic.coding.id"',
                        '"Recurrence.cosmic"',
                        '"Nombre_reference.cosmic"',
                        '"Histo_majoritaire.cosmic"',
                        '"Histo_majoritaire_pourcentage.cosmic"',
                        '"Clinvar.clinical.significance"',
                        '"Clinvar.review.status"',
                        '"MAF"',
                        '"Position_recurrenceB"',
                        '"Position_recurrence1B"',
                        '"Position_recurrence1_detail.N"',
                        '"is.driver"',
                        '"Temps"',
                        '"ORIGINE"',
                        '"RatioAlt_PosNeg"',
                        '"testN.R"',
                        '"testN.D"',
                        '"testN_recurrence"',
                        '"testN_id.N"',
                        '"Feature.type"',
                        '"SIFT"',
                        '"PROVEAN"',
                        '"Phastcons"',
                        '"Spidex.dpsi.max.tissue"',
                        '"dbscsnv.Ada.score"',
                        '"dbscsnv.Rf.score"',
                        '"Putative.impact"',
                        '"CADD.phred"',
                        '"FATHMM"',
                        '"MUTATIONTASTER"',
                        '"Read.background.enrichment"',
                        '"Torrent.server.metric"',
                        '"Fisher.test.p.value"',
                        '"Spidex.dpsi.z.score"',
                        '"NbrReadRef.Pos"',
                        '"NbrReadRef.Neg"',
                        '"NChar_Alt"',
                        '"NChar_Ref"',
                        '"SDlong"',
                        '"dlong"',
                        '"rlong"',
                        '"Depth_min"',
                        '"SDlong.1"',
                        '"dlong.1"',
                        '"rlong.1"',
                        '"Gene.mediane"',
                        '"Position.mediane1"',
                        '"Position.mediane"',
                        '"Position.medianeR"',
                        '"VAFsum"',
                        '"NChar_Alt.median"',
                        '"NChar_Ref.median"',
                        '"RatioAlt_PosNeg.Sample_id"',
                        '"RatioAlt_PosNeg.median1"',
                        '"Test"',
                        '"TRI"',
                    ],
                    "tables": [{"expression": "{main_table}", "alias": "main_table"}],
                    "filter": {
                        "filter_type": "AND",
                        "children": [
                            {"expression": "main_table.\"VAF color\" = 'FFFF0000'"},
                            {
                                "expression": "main_table.\"Background color\" NOT IN ('FF000000', '000000')"
                            },
                        ],
                    },
                    "order_by": [
                        {"field": "main_table.Chrom", "order": "ASC"},
                        {"field": "main_table.Position", "order": "ASC"},
                    ],
                }
            },
        },
        "final": {
            "query": {
                "select": {
                    "fields": [
                        '42 AS ".validation_hash"',
                        "'#'||\"Background color\" AS '.backgroundcolor'",
                        "'#'||\"VAF color\" as '.vafcolor'",
                        '"SUIVI/DIAGNOSTIC"',
                        '"Project.recurrence"',
                        '"Recurrence.cosmic"',
                        '"Phastcons"',
                        '"NbrReadAlt.Neg"',
                        '"NChar_Ref"',
                        '"dbsnp.rs.id"',
                        '"NbrReadAlt.Pos"',
                        '"VAF"',
                        "'#'||\"VAF color\" AS '.vafcolor'",
                        '"TRI"',
                        '"hgvs.c"',
                        '"Cosmic.noncoding.id"',
                        '"dbscsnv.Ada.score"',
                        '"N.Ref"',
                        '"Cosmic.coding.id"',
                        '"NbrReadRef.Pos"',
                        '"Spidex.dpsi.max.tissue"',
                        '"NChar_Alt"',
                        '"Analysis_recurrence.N"',
                        '"is.driver"',
                        '"Depth_min"',
                        '"dlong"',
                        '"Variant.effect"',
                        '"Clinvar.clinical.significance"',
                        '"Glims"',
                        '"Position"',
                        '"PROVEAN"',
                        '"NbrReadAlt"',
                        '"MUTATIONTASTER"',
                        '"SIFT"',
                        '"Feature.type"',
                        '"Fisher.test.p.value"',
                        '"SDlong"',
                        '"Torrent.server.metric"',
                        '"RatioAlt_PosNeg"',
                        '"Histo_majoritaire_pourcentage.cosmic"',
                        '"testN_recurrence"',
                        '"Clinvar.review.status"',
                        '"CADD.phred"',
                        '"dbscsnv.Rf.score"',
                        '"Histo_majoritaire.cosmic"',
                        '"Chrom"',
                        "'#'||\"Background color\" AS '.backgroundcolor'",
                        '"Background color"',
                    ],
                    "tables": [{"expression": "{main_table}", "alias": "main_table"}],
                    "filter": {
                        "filter_type": "AND",
                        "children": [
                            {"expression": "main_table.\"VAF color\" = 'FFFF0000'"},
                            {"expression": "main_table.\"SUIVI/DIAGNOSTIC\" = 'SUIVI'"},
                        ],
                    },
                    "order_by": [
                        {"field": "main_table.Chrom", "order": "ASC"},
                        {"field": "main_table.Position", "order": "ASC"},
                    ],
                }
            }
        },
    },
    "validation_ppi": {
        "genes_list": {
            "DREPANOCYTOSE": [
                "HBA1",
                "HBA2",
                "HBB",
                "G6PD",
                "UGT1A1",
                "PKLR",
                "CYB5R3",
                "HMOX1",
                "APOL1",
                "PIEZO1",
                "HBS1L",
                "SLC40A1",
                "BCL11A",
                "HbG2",
                "KL",
                "SCN11A",
            ],
            "THALASSEMIE": [
                "HBA1",
                "HBA2",
                "HBB",
                "G6PD",
                "UGT1A1",
                "PKLR",
                "HBS1L",
                "BCL11A",
            ],
            "MALADIE DE GILBERT / DEFICIT EN PYRUVATE KINASE": [
                "G6PD",
                "UGT1A1",
                "PKLR",
            ],
            "HB VARIANT": ["HBA1", "HBA2", "HBB", "CYB5R3", "BPGM"],
            "HEMOLYSE": [
                "PKLR",
                "HBB",
                "HBA2",
                "HBA1",
                "G6PD",
                "CYB5R3",
                "BPGM",
                "GPI",
                "TPI1",
                "PIEZO1",
                "APOL1",
            ],
            "SURFACTANT": [
                "COPA",
                "SFTPB",
                "SFTPC",
                "NKX2-1",
                "ABCA3",
                "FOXF1",
                "TBX4",
                "MARS1",
            ],
            "SCN": ["SCN9A", "SCN10A", "SCN11A"],
            "LMNA": ["LMNA"],
            "HFE": ["HFE"],
            "CFTR": ["CFTR"],
            "TTR": ["TTR"],
            "HBG2": ["HBG2"],
            "HMOX1": ["HMOX1"],
            "ALAS2": ["ALAS2"],
            "GLA": ["GLA"],
            "SRY": ["SRY"],
        },
        "variant_info_url_templates": [
            {"name": "VarSome", "url": "https://varsome.com/variant/hg19/{rsid}"}
        ],
        "default": {
            "title": "Presets de base",
            "description": "<body>Met \u00e0 disposition les champs les plus utiles.</body>",
            "query": {
                "select": {
                    "fields": [
                        "MAP{{'A':'red','C':'green','G':'blue','T':'black'}}[main_table.reference] AS '.refcolor'",
                        "MAP{{ 'missense_variant':'red', 'synonymous_variant':'green' }}[main_table.snpeff_Annotation] AS '.annotationcolor'",
                        "main_table.validation_hash AS '.validation_hash'",
                        "main_table.variant_hash AS '.variant_hash'",
                        "main_table.run_name AS '.run_name'",
                        "main_table.run_name AS 'Nom du run'",
                        "main_table.sample_name AS '.sample_name'",
                        "main_table.sample_name AS '\u00c9chantillon'",
                        "main_table.\"snpeff_HGVS.c\" AS 'c. de l anomalie'",
                        "main_table.\"snpeff_HGVS.p\" AS 'p. de l anomalie'",
                        "main_table.snpeff_Gene_Name AS 'Nom du g\u00e8ne'",
                        "main_table.snpeff_Feature_ID AS '.nm'",
                        "main_table.snpeff_Feature_ID AS 'NM'",
                        "concat(main_table.chromosome,'-',main_table.position,'-',main_table.reference,'-',main_table.alternate) AS 'Chr-Position-REF-ALT'",
                        "main_table.position AS '.Position'",
                        "main_table.reference AS '.All\u00e8le de r\u00e9f\u00e9rence'",
                        "main_table.alternate AS '.All\u00e8le alternatif'",
                        "floor(1e2 * main_table.cv_AF) / 1e2 AS 'Fr\u00e9quence all\u00e9lique'",
                        "MAP{{-1:'UNK',0:'REF',1:'HET',2:'HOM'}}[main_table.cv_GT] AS 'G\u00e9notype'",
                        "info_AC_raw AS 'Allele count Gnomad(exome)'",
                        "floor(1e5 * \"info_AF_raw\") / 1e5 AS 'Frequence Gnomad(exome)'",
                        "info_Hom_raw AS 'Nombre d''Homozygote (exome)'",
                        "if(len(main_table.reference)>len(main_table.alternate),'deletion',if(len(main_table.reference)<len(main_table.alternate),'insertion','substitution')) AS 'Famille de l anomalie'",
                        "main_table.snpeff_Annotation AS 'Annotation'",
                        "main_table.snpeff_Annotation_Impact AS 'Annotation impact'",
                        "agg.var_count AS 'Nombre de variants d\u00e9tect\u00e9s dans la base'",
                        "agg.hom_count AS 'Nombre d''homozygotes dans la base'",
                        "agg.het_count AS 'Nombre d''h\u00e9t\u00e9rozygotes dans la base'",
                        "recur.count AS 'Nombre d''observations du variant dans ce run'",
                        "refseq_contigs.refseq AS '.NC'",
                        "main_table.identifier[1] AS '.rsid'",
                        "user_table.accepted AS '.accepted'",
                        "user_table.comment AS '.comment'",
                        "user_table.tags AS '.tags'",
                        "if(contains(main_table.snpeff_Annotation,'intron_variant'), TRY_CAST (regexp_extract(main_table.\"snpeff_HGVS.c\",'[\\+|-](\\d+)', 1) AS INT16), 0) AS 'Distance de l exon'",
                        "if(user_table.accepted = true,'OUI','NON') AS 'Valid\u00e9 ?'",
                        "if(user_table.accepted IS NULL,'#A1A1A1',MAP{{true:'green',false:'#A1A1A1'}}[user_table.accepted]) AS '.accepted_color'",
                    ],
                    "tables": [
                        {"expression": "{main_table}", "alias": "main_table"},
                        {
                            "expression": "{user_table}",
                            "alias": "user_table",
                            "on": "main_table.validation_hash = user_table.validation_hash",
                            "how": "LEFT OUTER",
                        },
                        {
                            "expression": "read_parquet('{pwd}/aggregates/variants.parquet')",
                            "alias": "agg",
                            "on": "main_table.variant_hash = agg.variant_hash",
                            "how": "",
                        },
                        {
                            "select": {
                                "fields": ["variant_hash", "COUNT(*) as count"],
                                "tables": [
                                    {
                                        "select": {
                                            "fields": [
                                                "DISTINCT(sample_name)",
                                                "variant_hash",
                                            ],
                                            "tables": [
                                                {
                                                    "expression": "{main_table}",
                                                    "alias": "",
                                                }
                                            ],
                                        },
                                        "alias": "",
                                    }
                                ],
                                "group_by": ["variant_hash"],
                            },
                            "alias": "recur",
                            "on": "main_table.variant_hash = recur.variant_hash",
                            "how": "",
                        },
                        {
                            "expression": "read_csv('{pwd}/lists/liste_nms.csv',sep=',',header=false,names=['NM'])",
                            "alias": "nms",
                            "on": "split(main_table.snpeff_Feature_ID,'.')[1] = split(nms.NM,'.')[1]",
                            "how": "",
                        },
                        {
                            "expression": "read_csv('{pwd}/annotations/ucscToRefSeq.txt.gz',header=False,names=['contig','_1','_2','refseq'])",
                            "alias": "refseq_contigs",
                            "on": "main_table.chromosome = refseq_contigs.contig",
                            "how": "",
                        },
                    ],
                    "filter": {
                        "filter_type": "AND",
                        "children": [
                            {
                                "expression": "main_table.sample_name IN {selected_samples}"
                            },
                            {
                                "expression": "main_table.snpeff_Gene_Name IN {selected_genes}"
                            },
                        ],
                    },
                    "order_by": [
                        {"field": 'main_table."validation_hash"', "order": "DESC"}
                    ],
                }
            },
        },
        "final": {
            "query": {
                "select": {
                    "fields": [
                        "'hg19' AS 'Version genome' ",
                        "regexp_replace(main_table.sample_name,'-[MF]?_S\\d+$','') AS 'Sample ID'",
                        "'Mutation ponctuelle' AS 'Famille de l anomalie' ",
                        "upper(main_table.snpeff_Gene_Name)||' '||main_table.\"snpeff_HGVS.c\"||', '||main_table.\"snpeff_HGVS.p\" AS 'Libelle de l anomalie'",
                        "main_table.chromosome AS Chr",
                        "upper(main_table.snpeff_Gene_Name) AS 'Nom du gene'",
                        "hgnc.name AS 'Code HGNC'",
                        "main_table.snpeff_Feature_ID AS 'NM'",
                        "main_table.snpeff_Annotation AS 'Type region'",
                        "format('{{:02d}}', if(contains(main_table.snpeff_Rank,'/'), CAST (split(main_table.snpeff_Rank,'/')[1] AS INT16),0) ) AS 'Sequence region'",
                        "main_table.position AS 'Start'",
                        "main_table.position AS 'End'",
                        "main_table.reference AS Ref",
                        "main_table.alternate AS Alt",
                        "main_table.format_AD[1] AS 'Ref allele count'",
                        "main_table.format_AD[2] AS 'Alt allele count'",
                        "round(main_table.cv_AF,5) AS 'VAF'",
                        "main_table.\"snpeff_HGVS.c\" AS 'c. de l anomalie'",
                        "main_table.\"snpeff_HGVS.p\" AS 'p. de l anomalie'",
                        "'g.'||main_table.chromosome||'-'||main_table.position||main_table.reference||'-'||main_table.alternate AS 'g. de l anomalie'",
                        "main_table.snpeff_Annotation AS 'Consequence fonctionnelle de l anomalie'",
                        "main_table.identifier[1] as 'rsID'",
                        "user_table.clnacc AS 'Num\u00e9ro d''accession clinvar'",
                        "user_table.clnsig AS 'Signification CLINVAR'",
                        "MAP{{0:'R\u00e9f\u00e9rence',1:'H\u00e9t\u00e9rozygote',2:'Homozygote'}}[cv_GT] AS 'Statut du resultat'",
                        "'Detecte' AS 'Statut de detection'",
                        "user_table.acmg_classification AS 'Pathogenicite de l anomalie'",
                        "user_table.distribution_anomalie AS 'Distribution de l anomalie'",
                        "'SMAUG V2.4' AS 'Pipe SMAUG'",
                        "'PPI' AS 'Projet SMAUG'",
                        "main_table.validation_hash AS '.validation_hash'",
                    ],
                    "tables": [
                        {"expression": "{main_table}", "alias": "main_table"},
                        {
                            "expression": "{user_table}",
                            "alias": "user_table",
                            "on": "main_table.validation_hash = user_table.validation_hash",
                            "how": "",
                        },
                        {
                            "expression": "read_parquet('{pwd}/aggregates/variants.parquet')",
                            "alias": "agg",
                            "on": "main_table.variant_hash = agg.variant_hash",
                            "how": "",
                        },
                        {
                            "select": {
                                "fields": ["variant_hash", "COUNT(*) as recur_count"],
                                "tables": [
                                    {
                                        "select": {
                                            "fields": [
                                                "DISTINCT(sample_name)",
                                                "variant_hash",
                                            ],
                                            "tables": [
                                                {
                                                    "expression": "{main_table}",
                                                    "alias": "",
                                                }
                                            ],
                                        },
                                        "alias": "",
                                    }
                                ],
                                "group_by": ["variant_hash"],
                            },
                            "alias": "recur",
                            "on": "main_table.variant_hash = recur.variant_hash",
                            "how": "",
                        },
                        {
                            "select": {
                                "fields": ["name", "symbol"],
                                "tables": [
                                    {
                                        "expression": "read_parquet('{pwd}/annotations/hgnc.hg19.parquet')"
                                    }
                                ],
                            },
                            "alias": "hgnc",
                            "on": "main_table.snpeff_Gene_Name = hgnc.symbol",
                            "how": "",
                        },
                    ],
                    "order_by": [
                        {"field": "main_table.chromosome", "order": "DESC"},
                        {"field": "main_table.position", "order": "DESC"},
                    ],
                }
            }
        },
    },
}
