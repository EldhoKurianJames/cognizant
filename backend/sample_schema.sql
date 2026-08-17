-- Sample analytics schema and demo data for the text-to-SQL app.
-- Run against your PostgreSQL database, e.g.:
--   psql "$DATABASE_URL" -f sample_schema.sql

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    signup_date DATE NOT NULL,
    country VARCHAR(100)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed'
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL
);

INSERT INTO customers (name, email, signup_date, country) VALUES
('Alice Johnson', 'alice@example.com', '2024-01-15', 'USA'),
('Bob Smith', 'bob@example.com', '2024-02-20', 'UK'),
('Carla Diaz', 'carla@example.com', '2024-03-05', 'Spain'),
('David Lee', 'david@example.com', '2023-11-10', 'USA'),
('Eva Müller', 'eva@example.com', '2024-04-18', 'Germany');

INSERT INTO products (name, category, price) VALUES
('Wireless Mouse', 'Electronics', 25.99),
('Mechanical Keyboard', 'Electronics', 79.99),
('Standing Desk', 'Furniture', 349.00),
('Office Chair', 'Furniture', 189.50),
('Notebook Set', 'Stationery', 12.00);

INSERT INTO orders (customer_id, order_date, status) VALUES
(1, '2024-05-01', 'completed'),
(1, '2024-06-10', 'completed'),
(2, '2024-05-15', 'completed'),
(3, '2024-06-01', 'completed'),
(4, '2024-01-20', 'completed'),
(5, '2024-06-20', 'completed');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 2, 25.99),
(1, 3, 1, 349.00),
(2, 2, 1, 79.99),
(3, 4, 1, 189.50),
(4, 5, 3, 12.00),
(5, 2, 2, 79.99),
(6, 1, 1, 25.99),
(6, 5, 5, 12.00);
