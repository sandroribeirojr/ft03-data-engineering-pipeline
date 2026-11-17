CREATE OR REPLACE TABLE countries AS

        SELECT
            country_iso3,
            country_iso2,
            country_name,
            official_name,
            region,
            subregion,
            population,
            area_km2,
            latitude,
            longitude,
            capitals_json,
            languages_json,
            currencies_json

        FROM countries_staging

        WHERE country_iso3 IS NOT NULL
          AND country_name IS NOT NULL;


CREATE OR REPLACE TABLE country_capitals AS

        SELECT
            c.country_iso3,

            json_extract_string(
                item.value,
                '$.name'
            ) AS capital_name,

            TRY_CAST(
                json_extract_string(
                    item.value,
                    '$.coordinates.lat'
                ) AS DOUBLE
            ) AS latitude,

            TRY_CAST(
                json_extract_string(
                    item.value,
                    '$.coordinates.lng'
                ) AS DOUBLE
            ) AS longitude

        FROM countries c

        CROSS JOIN LATERAL json_each(
            c.capitals_json::JSON
        ) AS item;


CREATE OR REPLACE TABLE country_languages AS

        SELECT
            c.country_iso3,

            json_extract_string(
                item.value,
                '$.name'
            ) AS language_name,

            json_extract_string(
                item.value,
                '$.native_name'
            ) AS native_name,

            json_extract_string(
                item.value,
                '$.iso639_1'
            ) AS language_code

        FROM countries c

        CROSS JOIN LATERAL json_each(
            c.languages_json::JSON
        ) AS item;


CREATE OR REPLACE TABLE country_currencies AS

        SELECT
            c.country_iso3,

            json_extract_string(
                item.value,
                '$.code'
            ) AS currency_code,

            json_extract_string(
                item.value,
                '$.name'
            ) AS currency_name,

            json_extract_string(
                item.value,
                '$.symbol'
            ) AS currency_symbol

        FROM countries c

        CROSS JOIN LATERAL json_each(
            c.currencies_json::JSON
        ) AS item;
