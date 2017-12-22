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
stypes: sensor, switch, camera
INSERT INTO signals(name, stype, url, attributes) VALUES('Living room','sensor','http://172.16.229.187:8080','{}');
INSERT INTO signals(name, stype, url, attributes) VALUES('Back icicles','switch','http://172.16.229.252:8080','{}');
INSERT INTO signals(name, stype, url, attributes) VALUES('Backyard light','switch','http://172.16.229.51:8080','{}');
INSERT INTO signals(name, stype, url, attributes) VALUES('Front icicles ','switch','http://172.16.229.177:8080','{}');
INSERT INTO signals(name, stype, url, attributes) VALUES('Back camera','camera','http://172.16.229.21:8080','{}');
INSERT INTO signals(name, stype, url, attributes) VALUES('Front camera','camera','http://172.16.229.22:8080','{}'); 
/*