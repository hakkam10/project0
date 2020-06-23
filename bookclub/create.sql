CREATE TABLE reviews (
  username VARCHAR UNIQUE,
  isbn VARCHAR NOT NULL,
  comment VARCHAR,
  rating INTEGER
)
