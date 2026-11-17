-- Fatos sem correspondencia na dimensao de paises
SELECT COUNT(*)
FROM fact_economic_indicator f
LEFT JOIN countries c USING (country_iso3)
WHERE c.country_iso3 IS NULL;

-- Reconciliacao dos registros economicos
SELECT
    (SELECT COUNT(*) FROM economic_indicators),
    (SELECT COUNT(*) FROM fact_economic_indicator),
    (SELECT COUNT(*) FROM economic_unmatched);
