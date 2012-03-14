DROP VIEW Has_Wildcards;
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
       broken BOOLEAN,
       wildcards INET[] DEFAULT NULL);

CREATE INDEX index_tests_domain ON Tests(domain);
CREATE INDEX index_tests_date ON Tests(date);
CREATE INDEX index_zones_name ON Zones(name);
CREATE INDEX index_zones_uuid ON Zones(uuid);

CREATE VIEW Has_Wildcards AS SELECT * FROM Tests WHERE 
   array_upper(wildcards, 1) > 0;

CREATE OR REPLACE FUNCTION num_wildcards(TEXT) RETURNS INTEGER AS
    'SELECT (array_upper(wildcards, 1) - array_lower(wildcards, 1) + 1) FROM Tests
                     WHERE domain=$1;'
   LANGUAGE SQL;
