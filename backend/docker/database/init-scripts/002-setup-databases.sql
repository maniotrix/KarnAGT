-- Initial Database Setup
-- This script creates basic database structure for all environments

-- Create application-specific schemas
CREATE SCHEMA IF NOT EXISTS app_data;
CREATE SCHEMA IF NOT EXISTS app_analytics;
CREATE SCHEMA IF NOT EXISTS app_logs;

-- Create basic monitoring tables
CREATE TABLE IF NOT EXISTS app_data.database_info (
    id SERIAL PRIMARY KEY,
    environment VARCHAR(50) NOT NULL,
    version VARCHAR(50),
    initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert environment info (will be overwritten on each startup)
DELETE FROM app_data.database_info;
INSERT INTO app_data.database_info (environment, version) 
VALUES (current_setting('app.environment', true), '1.0.0');

-- Set default search path
ALTER DATABASE "{{ .Env.POSTGRES_DB }}" SET search_path TO app_data, public;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA app_data TO PUBLIC;
GRANT USAGE ON SCHEMA app_analytics TO PUBLIC;
GRANT USAGE ON SCHEMA app_logs TO PUBLIC;
