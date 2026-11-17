COPY fact_economic_indicator
TO '{output_path}'
(
    FORMAT PARQUET,
    COMPRESSION SNAPPY,
    PARTITION_BY (year),
    OVERWRITE_OR_IGNORE TRUE
);
