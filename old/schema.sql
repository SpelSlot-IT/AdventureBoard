-- Schema for MySQL database `DB_NAME`
-- Run this after creating or switching to the target database

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    privilege_level INT NOT NULL DEFAULT 0,
    karma INT DEFAULT 1000
);

CREATE TABLE IF NOT EXISTS adventures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    short_description TEXT NOT NULL,
    user_id INT,
    max_players INT NOT NULL DEFAULT 5,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_story_adventure BOOLEAN NOT NULL DEFAULT FALSE,
    requested_room VARCHAR(4),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS adventure_assignments (
    user_id INT NOT NULL,
    adventure_id INT NOT NULL,
    appeared BOOLEAN NOT NULL DEFAULT TRUE,
    top_three BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, adventure_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (adventure_id) REFERENCES adventures(id)
);

CREATE TABLE IF NOT EXISTS signups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    adventure_id INT NOT NULL,
    priority INT NOT NULL,
    UNIQUE KEY unique_user_adventure (user_id, adventure_id),
    UNIQUE KEY unique_user_priority (user_id, priority),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (adventure_id) REFERENCES adventures(id)
);

CREATE TABLE IF NOT EXISTS variable_storage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    release_state BOOLEAN NOT NULL DEFAULT FALSE
);

-- Ensure one row to hold release_state
INSERT IGNORE INTO variable_storage (id, release_state) VALUES (1, FALSE);