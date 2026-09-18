{{ config(materialized='table', schema='intermediate') }}
WITH dedup AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY date_reported, country_code ORDER BY loaded_at DESC) AS rn
    FROM {{ ref('stg_who_covid') }}
)
SELECT
    covid_record_key, date_reported, country_code,
    CASE country_name_raw
        WHEN 'United States of America' THEN 'United States'
        WHEN 'Russian Federation' THEN 'Russia'
        ELSE country_name_raw
    END AS country_name,
    who_region,
    CASE WHEN new_cases < 0 THEN 0 ELSE new_cases END AS new_cases,
    CASE WHEN cumulative_cases < 0 THEN 0 ELSE cumulative_cases END AS cumulative_cases,
    CASE WHEN new_deaths < 0 THEN 0 ELSE new_deaths END AS new_deaths,
    CASE WHEN cumulative_deaths < 0 THEN 0 ELSE cumulative_deaths END AS cumulative_deaths,
    ROUND(AVG(new_cases) OVER (PARTITION BY country_code ORDER BY date_reported ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS new_cases_7day_avg,
    ROUND(AVG(new_deaths) OVER (PARTITION BY country_code ORDER BY date_reported ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS new_deaths_7day_avg,
    CASE WHEN cumulative_cases > 0 THEN ROUND(cumulative_deaths::FLOAT / cumulative_cases::FLOAT * 100, 4) ELSE 0 END AS case_fatality_rate
FROM dedup WHERE rn = 1
