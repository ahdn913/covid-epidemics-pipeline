{{ config(materialized='table', schema='marts_core') }}
SELECT DISTINCT
    md5(country_code) AS country_key,
    country_code,
    country_name,
    who_region,
    CASE who_region
        WHEN 'AFRO' THEN 'Africa'
        WHEN 'AMRO' THEN 'Americas'
        WHEN 'SEARO' THEN 'Asia'
        WHEN 'EURO' THEN 'Europe'
        WHEN 'EMRO' THEN 'Eastern Mediterranean'
        WHEN 'WPRO' THEN 'Western Pacific'
        ELSE 'Other'
    END AS continent
FROM {{ ref('int_covid_cleaned') }}
WHERE country_code IS NOT NULL
