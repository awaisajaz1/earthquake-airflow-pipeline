-- Sample Queries for Earthquake Data Analysis
-- Use these queries in pgAdmin or psql to explore your earthquake data

-- Connect to earth database first
\c earth;

-- 1. Basic Data Exploration
-- View recent earthquakes
SELECT 
    id,
    magnitude,
    place,
    time_occurred,
    latitude,
    longitude,
    depth
FROM earthquake_data 
ORDER BY time_occurred DESC 
LIMIT 10;

-- 2. Magnitude Analysis
-- Count earthquakes by magnitude range
SELECT 
    CASE 
        WHEN magnitude < 3.0 THEN 'Minor (< 3.0)'
        WHEN magnitude < 4.0 THEN 'Light (3.0-3.9)'
        WHEN magnitude < 5.0 THEN 'Moderate (4.0-4.9)'
        WHEN magnitude < 6.0 THEN 'Strong (5.0-5.9)'
        WHEN magnitude < 7.0 THEN 'Major (6.0-6.9)'
        ELSE 'Great (7.0+)'
    END as magnitude_category,
    COUNT(*) as earthquake_count,
    AVG(magnitude) as avg_magnitude
FROM earthquake_data 
GROUP BY 
    CASE 
        WHEN magnitude < 3.0 THEN 'Minor (< 3.0)'
        WHEN magnitude < 4.0 THEN 'Light (3.0-3.9)'
        WHEN magnitude < 5.0 THEN 'Moderate (4.0-4.9)'
        WHEN magnitude < 6.0 THEN 'Strong (5.0-5.9)'
        WHEN magnitude < 7.0 THEN 'Major (6.0-6.9)'
        ELSE 'Great (7.0+)'
    END
ORDER BY MIN(magnitude);

-- 3. Geographic Analysis
-- Top 10 locations with most earthquakes
SELECT 
    place,
    COUNT(*) as earthquake_count,
    AVG(magnitude) as avg_magnitude,
    MAX(magnitude) as max_magnitude
FROM earthquake_data 
WHERE place IS NOT NULL
GROUP BY place 
ORDER BY earthquake_count DESC 
LIMIT 10;

-- 4. Time-based Analysis
-- Earthquakes by day of week
SELECT 
    EXTRACT(DOW FROM time_occurred) as day_of_week,
    CASE EXTRACT(DOW FROM time_occurred)
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    COUNT(*) as earthquake_count,
    AVG(magnitude) as avg_magnitude
FROM earthquake_data 
WHERE time_occurred IS NOT NULL
GROUP BY EXTRACT(DOW FROM time_occurred)
ORDER BY day_of_week;

-- 5. Significant Events
-- Earthquakes with magnitude >= 5.0 or tsunami alerts
SELECT 
    id,
    magnitude,
    place,
    time_occurred,
    tsunami,
    alert,
    url
FROM earthquake_data 
WHERE magnitude >= 5.0 OR tsunami = 1
ORDER BY magnitude DESC;

-- 6. Data Quality Check
-- Check for missing or invalid data
SELECT 
    'Total Records' as metric,
    COUNT(*) as count
FROM earthquake_data
UNION ALL
SELECT 
    'Missing Magnitude' as metric,
    COUNT(*) as count
FROM earthquake_data 
WHERE magnitude IS NULL
UNION ALL
SELECT 
    'Missing Location' as metric,
    COUNT(*) as count
FROM earthquake_data 
WHERE latitude IS NULL OR longitude IS NULL
UNION ALL
SELECT 
    'Missing Time' as metric,
    COUNT(*) as count
FROM earthquake_data 
WHERE time_occurred IS NULL;

-- 7. Analytics Schema Queries
-- Daily earthquake statistics (from materialized view)
SELECT * FROM analytics.daily_earthquake_stats 
ORDER BY earthquake_date DESC 
LIMIT 7;

-- 8. Raw Data Audit
-- Check raw data processing status
SELECT 
    COUNT(*) as total_raw_records,
    COUNT(CASE WHEN processed = true THEN 1 END) as processed_records,
    COUNT(CASE WHEN processed = false THEN 1 END) as unprocessed_records,
    MIN(extraction_time) as first_extraction,
    MAX(extraction_time) as last_extraction
FROM raw_data.earthquake_raw;

-- 9. Pipeline Summary
-- Overall pipeline statistics
SELECT 
    COUNT(*) as total_earthquakes,
    MIN(time_occurred) as earliest_earthquake,
    MAX(time_occurred) as latest_earthquake,
    AVG(magnitude) as average_magnitude,
    MAX(magnitude) as strongest_earthquake,
    COUNT(CASE WHEN magnitude >= 5.0 THEN 1 END) as significant_earthquakes,
    COUNT(CASE WHEN tsunami = 1 THEN 1 END) as tsunami_events
FROM earthquake_data;

-- 10. Refresh Analytics (run this to update materialized views)
REFRESH MATERIALIZED VIEW analytics.daily_earthquake_stats;