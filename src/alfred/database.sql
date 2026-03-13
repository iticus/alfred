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
      active smallint NOT NULL,
      attributes jsonb
);
--stypes: sensor, switch, camera

--subscriptions
CREATE TABLE subscriptions (
      id serial PRIMARY KEY,
	  added_timestamp timestamp without time zone NOT NULL,
	  endpoint text,
      key text NOT NULL,
      auth_secret text NOT NULL
);
