-- Create earthquake data tables in the same database as Airflow
-- This keeps everything simple - one database for both Airflow metadata and earthquake data

-- Create earthquake data table
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

-- Grant permissions to airflow user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;