-- Database creation script for the Ip module

DROP VIEW V6_enabled;
DROP VIEW V6_full;
DROP VIEW Local_address;
DROP VIEW Ipv4mapped_address;
DROP VIEW SixToFour_address;
DROP VIEW Teredo_address;
DROP VIEW Orchid_address;

DROP TABLE Tests CASCADE;
DROP TABLE Broker;
DROP TABLE Zones;
DROP TABLE IP;

\i runs-create.sql

CREATE TABLE Zones (id SERIAL UNIQUE NOT NULL,
       zone TEXT UNIQUE NOT NULL);

CREATE TABLE Ip (id SERIAL UNIQUE NOT NULL,
       address INET UNIQUE NOT NULL);

CREATE TABLE Tests (id SERIAL UNIQUE NOT NULL,
       broker INTEGER NOT NULL,
       date TIMESTAMP NOT NULL DEFAULT now(),
       ip INTEGER NOT NULL REFERENCES Ip(id),
       cc TEXT DEFAULT NULL,
       asn INTEGER DEFAULT NULL,
       type TEXT DEFAULT NULL,
       result BOOLEAN DEFAULT NULL,
       details TEXT DEFAULT NULL,
       version_method TEXT DEFAULT NULL,
       version TEXT DEFAULT NULL);

CREATE TABLE Tests_zone () INHERITS (Tests);
CREATE TABLE Tests_ns_zone () INHERITS (Tests);
CREATE TABLE Tests_mx_zone () INHERITS (Tests);
CREATE TABLE Tests_www_zone () INHERITS (Tests);
CREATE TABLE Tests_www_ipv6_zone () INHERITS (Tests);

-- Inheritance does not propagate constraints, so we have to create them manually

ALTER TABLE Tests_zone ADD CONSTRAINT tests_zone_id_key UNIQUE (id);
ALTER TABLE Tests_ns_zone ADD CONSTRAINT tests_ns_zone_id_key UNIQUE (id);
ALTER TABLE Tests_mx_zone ADD CONSTRAINT tests_mx_zone_id_key UNIQUE (id);
ALTER TABLE Tests_www_zone ADD CONSTRAINT tests_www_zone_id_key UNIQUE (id);
ALTER TABLE Tests_www_ipv6_zone ADD CONSTRAINT tests_www_ipv6_zone_id_key UNIQUE (id);

ALTER TABLE Tests_zone ADD CONSTRAINT tests_zone_ip_fkey FOREIGN KEY (ip) REFERENCES Ip (id);
ALTER TABLE Tests_ns_zone ADD CONSTRAINT tests_ns_zone_ip_fkey FOREIGN KEY (ip) REFERENCES Ip (id);
ALTER TABLE Tests_mx_zone ADD CONSTRAINT tests_mx_zone_ip_fkey FOREIGN KEY (ip) REFERENCES Ip (id);
ALTER TABLE Tests_www_zone ADD CONSTRAINT tests_www_zone_ip_fkey FOREIGN KEY (ip) REFERENCES Ip (id);
ALTER TABLE Tests_www_ipv6_zone ADD CONSTRAINT tests_www_ipv6_zone_ip_fkey FOREIGN KEY (ip) REFERENCES Ip (id);
 
-- What about IPv6-specific names?
CREATE VIEW Tests_Web AS SELECT * FROM Tests_zone UNION SELECT * FROM Tests_www_zone;

CREATE TABLE Broker (id SERIAL UNIQUE NOT NULL,
       uuid UUID NOT NULL REFERENCES runs(UUID),
       zone INTEGER NOT NULL REFERENCES Zones(id),
       broken BOOLEAN);

ALTER TABLE Tests ADD CONSTRAINT tests_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);
ALTER TABLE Tests_zone ADD CONSTRAINT tests_zone_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);
ALTER TABLE Tests_ns_zone ADD CONSTRAINT tests_ns_zone_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);
ALTER TABLE Tests_mx_zone ADD CONSTRAINT tests_mx_zone_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);
ALTER TABLE Tests_www_zone ADD CONSTRAINT tests_www_zone_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);
ALTER TABLE Tests_www_ipv6_zone ADD CONSTRAINT tests_www_ipv6_zone_broker_fkey FOREIGN KEY (broker) REFERENCES Broker (id);

CREATE OR REPLACE FUNCTION store_zone (p_zone TEXT) RETURNS INTEGER AS $$
DECLARE
    id_zone INTEGER;
BEGIN
    LOCK TABLE Zones IN ACCESS EXCLUSIVE MODE;
    SELECT id INTO id_zone FROM Zones WHERE zone = p_zone;
    IF id_zone IS NULL THEN
        SELECT nextval('zones_id_seq') INTO id_zone;
        INSERT INTO zones (id, zone) VALUES (id_zone, p_zone);
    END IF;
    RETURN id_zone;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION store_ip (p_address INET) RETURNS INTEGER AS $$
DECLARE
    id_address INTEGER;
BEGIN
    LOCK TABLE Ip IN ACCESS EXCLUSIVE MODE;
    SELECT id INTO id_address FROM Ip WHERE address = p_address;
    IF id_address IS NULL THEN
        SELECT nextval('ip_id_seq') INTO id_address;
        INSERT INTO Ip (id, address) VALUES (id_address, p_address);
    END IF;
    RETURN id_address;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION store_broker (p_uuid UUID,
                                         p_id_zone INTEGER,
                                         p_broken BOOLEAN)
RETURNS INTEGER AS $$
DECLARE
    id_broker INTEGER;
BEGIN
    SELECT nextval('broker_id_seq') INTO id_broker;
    INSERT INTO Broker (id, uuid, zone, broken) VALUES (id_broker, p_uuid, p_id_zone, p_broken);
    RETURN id_broker;
END;
$$ LANGUAGE plpgsql;

-- CREATE TYPE TEST AS (ip INET, cc TEXT, asn INTEGER, type TEXT, result BOOLEAN, details TEXT, version_method TEXT, version TEXT);

CREATE OR REPLACE FUNCTION store_test (p_broker INTEGER,
                                       p_type TEXT,
                                       p_test TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    test TEXT[];
    id_ip INTEGER;
BEGIN
    SELECT regexp_split_to_array(p_test, E'\\|\\|\\|\\| +') INTO test;

    IF test[2] = '' THEN
        test[2] := NULL;
    END IF;

    IF test[3] = '' THEN
        test[3] := NULL;
    END IF;

    IF test[4] = '' THEN
        test[4] := NULL;
    END IF;

    IF test[5] = '' THEN
        test[5] := NULL;
    END IF;

    IF test[6] = '' THEN
        test[6] := NULL;
    END IF;

    IF test[7] = '' THEN
        test[7] := NULL;
    END IF;

    IF test[8] = '' THEN
        test[8] := NULL;
    END IF;

    SELECT store_ip(test[1]::INET) INTO id_ip;
    IF p_type = 'tests_zone' THEN
        INSERT INTO tests_zone (broker, ip, cc, asn, type, result, details, version_method, version) VALUES (p_broker,
                                                                           id_ip,
                                                                           test[2],
                                                                           test[3]::INTEGER,
                                                                           test[4],
                                                                           test[5]::BOOLEAN,
                                                                           test[6],
                                                                           test[7],
                                                                           test[8]);
    ELSIF p_type = 'tests_ns_zone' THEN
        INSERT INTO tests_ns_zone (broker, ip, cc, asn, type, result, details, version_method, version) VALUES (p_broker,
                                                                           id_ip,
                                                                           test[2],
                                                                           test[3]::INTEGER,
                                                                           test[4],
                                                                           test[5]::BOOLEAN,
                                                                           test[6],
                                                                           test[7],
                                                                           test[8]);
    ELSIF p_type = 'tests_mx_zone' THEN
        INSERT INTO tests_mx_zone (broker, ip, cc, asn, type, result, details, version_method, version) VALUES (p_broker,
                                                                           id_ip,
                                                                           test[2],
                                                                           test[3]::INTEGER,
                                                                           test[4],
                                                                           test[5]::BOOLEAN,
                                                                           test[6],
                                                                           test[7],
                                                                           test[8]);
    ELSIF p_type = 'tests_www_zone' THEN
        INSERT INTO tests_www_zone (broker, ip, cc, asn, type, result, details, version_method, version) VALUES (p_broker,
                                                                           id_ip,
                                                                           test[2],
                                                                           test[3]::INTEGER,
                                                                           test[4],
                                                                           test[5]::BOOLEAN,
                                                                           test[6],
                                                                           test[7],
                                                                           test[8]);
    ELSIF p_type = 'tests_www_ipv6_zone' THEN
        INSERT INTO tests_www_ipv6_zone (broker, ip, cc, asn, type, result, details, version_method, version) VALUES (p_broker,
                                                                           id_ip,
                                                                           test[2],
                                                                           test[3]::INTEGER,
                                                                           test[4],
                                                                           test[5]::BOOLEAN,
                                                                           test[6],
                                                                           test[7],
                                                                           test[8]);
    ELSE
        RETURN 'f';
    END IF;
    RETURN 't';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION store (p_uuid UUID,
                                  p_zone TEXT,
                                  p_broken BOOLEAN,
                                  p_test_zone TEXT[],
                                  p_test_ns_zone TEXT[],
                                  p_test_mx_zone TEXT[],
                                  p_test_www_zone TEXT[],
                                  p_test_www_ipv6_zone TEXT[])
RETURNS BOOLEAN AS $$
DECLARE
    id_zone INTEGER;
    id_broker INTEGER;
BEGIN
    SELECT store_zone(p_zone) INTO id_zone;
    SELECT store_broker(p_uuid, id_zone, p_broken) INTO id_broker;

    IF array_length(p_test_zone, 1) >= 1 THEN
        FOR i IN 1..array_length(p_test_zone, 1) LOOP
            PERFORM store_test (id_broker, 'tests_zone', p_test_zone[i]);
        END LOOP;
    END IF;

    IF array_length(p_test_ns_zone, 1) >= 1 THEN
        FOR i IN 1..array_length(p_test_ns_zone, 1) LOOP
            PERFORM store_test (id_broker, 'tests_ns_zone', p_test_ns_zone[i]);
        END LOOP;
    END IF;

    IF array_length(p_test_mx_zone, 1) >= 1 THEN
        FOR i IN 1..array_length(p_test_mx_zone, 1) LOOP
            PERFORM store_test (id_broker, 'tests_mx_zone', p_test_mx_zone[i]);
        END LOOP;
    END IF;

    IF array_length(p_test_www_zone, 1) >= 1 THEN
        FOR i IN 1..array_length(p_test_www_zone, 1) LOOP
            PERFORM store_test (id_broker, 'tests_www_zone', p_test_www_zone[i]);
        END LOOP;
    END IF;

    IF array_length(p_test_www_ipv6_zone, 1) >= 1 THEN
        FOR i IN 1..array_length(p_test_www_ipv6_zone, 1) LOOP
            PERFORM store_test (id_broker, 'tests_www_ipv6_zone', p_test_www_ipv6_zone[i]);
        END LOOP;
    END IF;

    RETURN 't';
END;
$$ LANGUAGE plpgsql;

CREATE VIEW V6_enabled AS SELECT b.uuid, z.* FROM Broker b, Zones z WHERE
       b.id IN (SELECT DISTINCT broker FROM Tests WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND b.zone = z.id;

CREATE VIEW V6_full AS SELECT b.uuid, z.* FROM Broker b, Zones z WHERE
            b.id IN (SELECT DISTINCT broker FROM Tests_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND
            b.id IN (SELECT DISTINCT broker FROM Tests_ns_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND
            b.id IN (SELECT DISTINCT broker FROM Tests_mx_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND
            b.id IN ((SELECT DISTINCT broker FROM Tests_www_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
            UNION
            (SELECT DISTINCT broker FROM Tests_www_ipv6_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6')))
       AND
            b.zone = z.id;

CREATE VIEW V6_Web AS SELECT b.uuid, z.* FROM Broker b, Zones z WHERE
       b.id IN ((SELECT DISTINCT broker FROM Tests_www_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       UNION
       (SELECT DISTINCT broker FROM Tests_www_ipv6_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6')))
       AND b.zone = z.id;

CREATE VIEW V6_DNS AS SELECT b.uuid, z.* FROM Broker b, Zones z WHERE
       b.id IN (SELECT DISTINCT broker FROM Tests_ns_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND b.zone = z.id;

CREATE VIEW V6_email AS SELECT b.uuid, z.* FROM Broker b, Zones z WHERE
       b.id IN (SELECT DISTINCT broker FROM Tests_mx_zone WHERE ip IN (SELECT id FROM Ip WHERE family(address) = '6'))
       AND b.zone = z.id;

---- http://www.iana.org/assignments/iana-ipv6-special-registry
---- http://www.postgresql.org/docs/8.3/interactive/functions-net.html
CREATE VIEW Local_address AS SELECT * FROM Ip WHERE
          NOT (address << '2000::/3') AND (family(address) = '6');
---- Actually, it is more than "local" addresses, it includes things
---- like ff::/8 (multicast)

CREATE VIEW SixToFour_address AS SELECT * FROM Ip WHERE
        (address << '2002::/16') OR (address << '2000::/32');

CREATE VIEW Ipv4mapped_address AS SELECT * FROM Ip WHERE
        (address << '::ffff:0.0.0.0/96');

CREATE VIEW Teredo_address AS SELECT * FROM Ip WHERE
        (address << '2001::/32');

CREATE VIEW Orchid_address AS SELECT * FROM Ip WHERE
        (address << '2001:10::/28');

---- Which zones use a given IP address? (IP addresses are stored in
---- PostgreSQL arrays.)
CREATE OR REPLACE FUNCTION uses(INET) RETURNS SETOF INTEGER AS
    'SELECT zone from Broker WHERE id IN (SELECT DISTINCT broker FROM Tests WHERE ip IN (SELECT id from Ip WHERE $1 >> address OR $1 = address));'
LANGUAGE SQL;

---- Example of use:
---- SELECT count(zone) FROM v6_enabled WHERE uuid='e2a04e7a-766f-4d8d-ad56-48b450ddecd4' \
----                AND id IN (SELECT uses('2a02:2b8::/32'));

