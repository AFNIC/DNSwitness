DROP TABLE Tests;
DROP TABLE Zones;

CREATE TABLE Zones (id SERIAL UNIQUE NOT NULL,
       uuid UUID NOT NULL,
       date TIMESTAMP NOT NULL DEFAULT now(),
       name TEXT NOT NULL); -- Not UNIQUE because several runs can be stored in the base

CREATE TABLE Tests (id SERIAL UNIQUE NOT NULL,
       uuid UUID NOT NULL,
       date TIMESTAMP NOT NULL DEFAULT now(),
       domain TEXT NOT NULL,
       zone INTEGER NOT NULL REFERENCES Zones(id),
       profile TEXT,
       status BOOLEAN,
       message TEXT);

\i runs-create.sql

CREATE INDEX index_tests_uuid ON Tests(uuid);
CREATE INDEX index_tests_domain ON Tests(domain);
CREATE INDEX index_tests_date ON Tests(date);
CREATE INDEX index_zones_name ON Zones(name);
CREATE INDEX index_zones_uuid ON Zones(uuid);

