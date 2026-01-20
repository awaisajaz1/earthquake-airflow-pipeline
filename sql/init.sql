-- Connect to the earth database for earthquake data
\c earth;

-- Create earthquake data table in earth database
CREATE TABLE IF NOT EXISTS earthquake_data (
    id VARCHAR(50) PRIMARY KEY,
    magnitude DECIMAL(4,2),
    place VARCHAR(255),
    time_occurred TIMESTAMP,
    updated_time TIMESTAMP,
    timezone INTEGER,
    url VARCHAR(500),
    detail_url VARCHAR(500),
    felt INTEGER,
    cdi DECIMAL(3,1),
    mmi DECIMAL(3,1),
    alert VARCHAR(10),
    status VARCHAR(20),
    tsunami INTEGER,
    sig INTEGER,
    net VARCHAR(10),
    code VARCHAR(20),
    ids VARCHAR(255),
    sources VARCHAR(255),
    types VARCHAR(255),
    nst INTEGER,
    dmin DECIMAL(8,3),
    rms DECIMAL(8,3),
    gap DECIMAL(5,1),
    magnitude_type VARCHAR(10),
    type VARCHAR(20),
    title VARCHAR(255),
    longitude DECIMAL(10,6),
    latitude DECIMAL(10,6),
    depth DECIMAL(8,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_earthquake_magnitude ON earthquake_data(magnitude);
CREATE INDEX IF NOT EXISTS idx_earthquake_time ON earthquake_data(time_occurred);
CREATE INDEX IF NOT EXISTS idx_earthquake_location ON earthquake_data(latitude, longitude);

-- Create a summary table for analytics
CREATE TABLE IF NOT EXISTS earthquake_summary (
    id SERIAL PRIMARY KEY,
    date_processed DATE,
    total_earthquakes INTEGER,
    max_magnitude DECIMAL(4,2),
    min_magnitude DECIMAL(4,2),
    avg_magnitude DECIMAL(4,2),
    significant_earthquakes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a schema for raw data (optional - for data lake approach)
CREATE SCHEMA IF NOT EXISTS raw_data;

-- Create raw earthquake data table (for backup/audit purposes)
CREATE TABLE IF NOT EXISTS raw_data.earthquake_raw (
    id SERIAL PRIMARY KEY,
    raw_json JSONB,
    extraction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

-- Create a schema for analytics and reporting
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create materialized view for quick analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_earthquake_stats AS
SELECT 
    DATE(time_occurred) as earthquake_date,
    COUNT(*) as total_earthquakes,
    AVG(magnitude) as avg_magnitude,
    MAX(magnitude) as max_magnitude,
    MIN(magnitude) as min_magnitude,
    COUNT(CASE WHEN magnitude >= 5.0 THEN 1 END) as significant_earthquakes,
    COUNT(CASE WHEN tsunami = 1 THEN 1 END) as tsunami_events
FROM earthquake_data
WHERE time_occurred IS NOT NULL
GROUP BY DATE(time_occurred)
ORDER BY earthquake_date DESC;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_stats_date ON analytics.daily_earthquake_stats(earthquake_date);

-- Grant permissions to airflow user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA raw_data TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_data TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw_data TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA analytics TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO airflow;