{{ config(materialized='table', schema='marts_epidemiology') }}
SELECT
    d.country_code, d.country_name, d.who_region, d.continent,
    MAX(f.cumulative_cases) AS total_cases,
    MAX(f.cumulative_deaths) AS total_deaths,
    MAX(f.new_cases) AS peak_daily_cases,
    ROUND(AVG(f.new_cases),2) AS avg_daily_cases,
    CASE WHEN MAX(f.cumulative_cases) > 0 THEN ROUND(MAX(f.cumulative_deaths)::FLOAT / MAX(f.cumulative_cases)::FLOAT * 100, 4) ELSE 0 END AS overall_cfr,
    MIN(f.date_reported) AS first_case_date,
    MAX(f.date_reported) AS last_report_date,
    SUM(CASE WHEN f.is_outbreak_day THEN 1 ELSE 0 END) AS outbreak_days_count
FROM {{ ref('fact_covid_daily') }} f
JOIN {{ ref('dim_country') }} d ON md5(f.country_code) = d.country_key
GROUP BY d.country_code, d.country_name, d.who_region, d.continent
ORDER BY MAX(f.cumulative_cases) DESC
