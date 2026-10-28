CREATE DATABASE IF NOT EXISTS netwatch
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE netwatch;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    description VARCHAR(255) DEFAULT '',
    last_status VARCHAR(10) DEFAULT 'Unknown',
    last_response_ms DECIMAL(10,2) NULL,
    last_checked DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitoring_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    status VARCHAR(10) NOT NULL,
    response_ms DECIMAL(10,2) NULL,
    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_logs_device FOREIGN KEY (device_id)
        REFERENCES devices(id) ON DELETE CASCADE
);
