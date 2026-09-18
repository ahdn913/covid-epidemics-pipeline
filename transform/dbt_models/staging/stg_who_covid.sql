{{ config(materialized='view', schema='staging') }}
SELECT
    md5(COALESCE(CAST(date_reported AS TEXT),'') || '_' || COALESCE(country_code,'')) AS covid_record_key,
    CAST(date_reported AS DATE) AS date_reported,
    UPPER(TRIM(country_code)) AS country_code,
    TRIM(country) AS country_name_raw,
    UPPER(TRIM(who_region)) AS who_region,
    COALESCE(new_cases,0) AS new_cases,
    COALESCE(cumulative_cases,0) AS cumulative_cases,
    COALESCE(new_deaths,0) AS new_deaths,
    COALESCE(cumulative_deaths,0) AS cumulative_deaths
FROM {{ source('staging','who_covid_raw') }}
