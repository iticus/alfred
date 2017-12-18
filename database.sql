--Postgres database structure for alfred

--users
CREATE TABLE users (
      id serial PRIMARY KEY,
      name text NOT NULL,
      username text UNIQUE NOT NULL,
      password text NOT NULL,
      level smallint NOT NULL
);
CREATE INDEX user_username_idx ON users USING btree(username);

--signals
CREATE TABLE signals (
      id serial PRIMARY KEY,
      name text NOT NULL,
      stype text NOT NULL,
      url text NOT NULL,
      attributes jsonb
);

/*
stypes: switch, camera 
/*