{{ config(materialized='table', schema='marts_core') }}
SELECT
    md5(COALESCE(CAST(c.date_reported AS TEXT),'') || '_' || COALESCE(c.country_code,'')) AS fact_key,
    TO_CHAR(c.date_reported, 'YYYYMMDD')::INTEGER AS date_key,
    md5(c.country_code) AS country_key,
    c.date_reported, c.country_code,
    c.new_cases, c.cumulative_cases, c.new_deaths, c.cumulative_deaths,
    c.case_fatality_rate, c.new_cases_7day_avg, c.new_deaths_7day_avg,
    GREATEST(c.cumulative_cases - c.cumulative_deaths, 0) AS estimated_active_cases,
    CASE WHEN c.new_cases > c.new_cases_7day_avg * 1.5 AND c.new_cases_7day_avg > 10 THEN TRUE ELSE FALSE END AS is_outbreak_day
FROM {{ ref('int_covid_cleaned') }} c
