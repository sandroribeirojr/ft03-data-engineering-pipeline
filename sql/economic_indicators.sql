
CREATE OR REPLACE TABLE economic_indicators AS
SELECT DISTINCT
    country_iso3,
    country_name,
    indicator_code,
    indicator_name,
    year,
    value,
    unit
FROM economic_staging;

    
CREATE OR REPLACE TABLE country_economic_data AS

        WITH indicators_pivot AS (

            SELECT
                e.country_iso3,
                e.year,

                MAX(
                    CASE
                        WHEN e.indicator_name = 'GDP'
                        THEN e.value
                    END
                ) AS gdp,

                MAX(
                    CASE
                        WHEN e.indicator_name = 'GDP_PER_CAPITA'
                        THEN e.value
                    END
                ) AS gdp_per_capita,

                MAX(
                    CASE
                        WHEN e.indicator_name = 'POPULATION'
                        THEN e.value
                    END
                ) AS wb_population,

                MAX(
                    CASE
                        WHEN e.indicator_name = 'LIFE_EXPECTANCY'
                        THEN e.value
                    END
                ) AS life_expectancy,

                MAX(
                    CASE
                        WHEN e.indicator_name = 'INFLATION'
                        THEN e.value
                    END
                ) AS inflation

            FROM economic_indicators e

            INNER JOIN countries c
                ON e.country_iso3 = c.country_iso3

            GROUP BY
                e.country_iso3,
                e.year
        )

        SELECT
            c.country_iso3,
            c.country_name,
            c.region,
            c.subregion,
            c.population AS rest_population,

            e.year,
            e.gdp,
            e.gdp_per_capita,
            e.wb_population,
            e.life_expectancy,
            e.inflation,

            MAKE_DATE(
                e.year,
                1,
                1
            ) AS reference_date

        FROM countries c

        LEFT JOIN indicators_pivot e
            ON c.country_iso3 = e.country_iso3

        ORDER BY
            c.country_name,
            e.year;



-- Indicadores associados aos paises cadastrados
CREATE OR REPLACE TABLE fact_economic_indicator AS
SELECT
    e.country_iso3,
    e.indicator_code,
    e.indicator_name,
    e.year,
    e.value,
    e.unit
FROM economic_indicators e
INNER JOIN countries c
    ON e.country_iso3 = c.country_iso3;


-- Indicadores sem correspondencia cadastral
CREATE OR REPLACE TABLE economic_unmatched AS
SELECT
    e.country_iso3,
    e.country_name,
    e.indicator_code,
    e.indicator_name,
    e.year,
    e.value,
    e.unit,
    CASE
        WHEN e.country_iso3 = 'XKX'
            THEN 'COUNTRY_NOT_MATCHED'
        ELSE 'AGGREGATE_OR_UNMATCHED'
    END AS rejection_reason
FROM economic_indicators e
LEFT JOIN countries c
    ON e.country_iso3 = c.country_iso3
WHERE c.country_iso3 IS NULL;
