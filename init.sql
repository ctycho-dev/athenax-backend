CREATE TABLE IF NOT EXISTS wishlists (
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);