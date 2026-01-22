-- Create earth_quake_db database
CREATE DATABASE earth_quake_db;

-- Grant permissions to airflow user
GRANT ALL PRIVILEGES ON DATABASE earth_quake_db TO airflow;

-- Connect to the new database and create the earthquake table
\c earth_quake_db;

CREATE TABLE IF NOT EXISTS earth_quake_data (
    id VARCHAR(255) PRIMARY KEY,
    place VARCHAR(255),
    magnitude FLOAT,
    time TIMESTAMP,
    longitude FLOAT,
    latitude FLOAT,
    depth FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions on the table
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;