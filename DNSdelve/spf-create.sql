DROP VIEW Different_Spf;
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
       spf TEXT,
       adsp TEXT);

\i runs-create.sql

CREATE INDEX index_tests_uuid ON Tests(uuid);
CREATE INDEX index_tests_domain ON Tests(domain);
CREATE INDEX index_tests_date ON Tests(date);
CREATE INDEX index_zones_name ON Zones(name);
CREATE INDEX index_zones_uuid ON Zones(uuid);

-- Some big hosters add automatically a SPF record for all their
-- zones. Try to find how many different SPF records there is
-- (warning, there is also the case of popular records such as "v=spf1
-- a mx ?all").

CREATE VIEW Different_Spf AS 
      SELECT DISTINCT spf, count(spf) AS number, uuid FROM Tests WHERE 
            spf IS NOT NULL GROUP BY spf, uuid;
-- SELECT number,spf FROM Different_Spf WHERE uuid='xxxxx' ORDER BY number DESC;
-- Other technique for a similar result:
-- SELECT spf, count(spf) FROM Tests GROUP BY spf HAVING count(spf) > 1 ORDER BY count DESC;

