CREATE TABLE IF NOT EXISTS users (
    id       INTEGER         PRIMARY KEY AUTOINCREMENT,
    username VARCHAR (20)    UNIQUE
                             NOT NULL,
    password VARCHAR (8, 16) NOT NULL
);


CREATE TABLE IF NOT EXISTS books (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER  REFERENCES users (id),
    isbn          INT (13) NOT NULL,
    title         TEXT     NOT NULL,
    author        TEXT     NOT NULL,
    page_count    INTEGER  NOT NULL,
    avg_rating    TEXT     NOT NULL,
    thumbnail_url TEXT     NOT NULL,
    UNIQUE (
        user_id,
        isbn
    )
);