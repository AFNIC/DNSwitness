DROP TABLE DNS_types;
DROP TABLE DNS_Packets CASCADE;
DROP TRIGGER trg_partitioning ON pcap_files;
DROP TRIGGER trg_partitioning2 ON pcap_files;
DROP TABLE PCAP_files;
DROP TYPE protocols;

CREATE TYPE protocols AS ENUM ('TCP', 'UDP');

CREATE TABLE Pcap_files(id SERIAL UNIQUE NOT NULL, 
       added TIMESTAMP NOT NULL DEFAULT now(), 
       hostname TEXT,
       filename TEXT UNIQUE NOT NULL, datalinktype TEXT, snaplength INTEGER, 
       filesize BIGINT, -- pcap files are often huge
       filedate TIMESTAMP,
       firstpacket TIMESTAMP, lastpacket TIMESTAMP,
       samplingrate FLOAT CHECK (samplingrate <= 1.0 AND samplingrate >= 0.0),
       stoppedat INTEGER, -- If we used the -m option, use that to indicate that
       -- we "truncated" the input file
       totalpackets INTEGER, storedpackets INTEGER);	

CREATE TABLE DNS_Packets (id SERIAL UNIQUE NOT NULL, 
       file INTEGER NOT NULL REFERENCES Pcap_files(id),
       rank INTEGER NOT NULL, -- Rank of the packet in the file
       date TIMESTAMP, -- Date of capture in UTC
       length INTEGER NOT NULL, -- Length on the cable, we may have stored 
                                -- less bytes
       added TIMESTAMP NOT NULL DEFAULT now(),
       src_address INET NOT NULL,
       dst_address INET  NOT NULL,
       protocol protocols  NOT NULL,     
       src_port INTEGER  NOT NULL,
       dst_port INTEGER  NOT NULL,
       -- Field names and semantic are found in RFC 1034 and 1035. We do not 
       -- try to be user-friendly
       query BOOLEAN   NOT NULL,
       query_id INTEGER   NOT NULL,
       opcode INTEGER   NOT NULL,
       rcode INTEGER  NOT NULL, 
       aa BOOLEAN  NOT NULL,
       tc BOOLEAN  NOT NULL,
       rd BOOLEAN  NOT NULL,
       ra BOOLEAN  NOT NULL,
       qclass INTEGER, -- NULL are allowed because this field was not always in the schema
       qname TEXT  NOT NULL, -- The raw version of the QNAME, without any processing (not even lowercasing)
       qtype INTEGER  NOT NULL, -- With helper functions TODO to translate numeric values to well-known text like AAAA, MX, etc
       edns0_size INTEGER, -- NULL if no EDNS0
       do_dnssec BOOLEAN, -- NULL if no EDNS0
       edns_options INTEGER[], -- NULL if no EDNS0
       ancount INTEGER  NOT NULL,
       nscount INTEGER  NOT NULL,
       arcount INTEGER  NOT NULL,
       -- All the columns above are directly obtained from the
       -- packet. They are sufficient for all the
       -- processings. However, both for performance reasons and for
       -- easying the task of the developers, some (optional) columns
       -- are computed at store-time. They are obtained only from the
       -- values above. So, the table, up to this line, is in first
       -- normal form, but it is not if you include the columns here:
       registered_domain TEXT, -- The part of the QNAME that was
			       -- registered such as example.fr for a
			       -- QNAME of www.example.fr or
			       -- durand.nom.fr for a QNAME of
			       -- mail.durand.nom.fr.
       lowercase_qname TEXT
       );

CREATE TABLE DNS_types (id SERIAL UNIQUE NOT NULL,
       type TEXT UNIQUE NOT NULL,
       value INTEGER UNIQUE NOT NULL,
       meaning TEXT,
       rfcreferences TEXT);

-- You need to install the plpgsql language:
-- http://www.postgresql.org/docs/8.1/static/xplang.html
CREATE OR REPLACE FUNCTION partitioning() RETURNS TRIGGER AS $trg_partitioning$
    DECLARE
        table_name TEXT = 'dns_packets_' || NEW.id;
    BEGIN
        EXECUTE 'CREATE TABLE ' || table_name || ' (check (file = ' || NEW.id ||')) INHERITS (dns_packets);';
        -- It is way quicker to create indexes and constraints AFTER inserting.
        -- http://www.postgresql.org/docs/8.4/static/populate.html
        -- Here we leave this to the client.
        RETURN NEW;
    END;
$trg_partitioning$ LANGUAGE plpgsql;

--CREATE TRIGGER trg_partitioning AFTER INSERT ON pcap_files
--    FOR EACH ROW EXECUTE PROCEDURE partitioning();


-- Using the same sequence for column 'id' for all 'dns_packets_*' tables leads to trouble : 
--  column 'id' type is int ==> max value = 2 147 483 648 
-- while  sequence 'dns_packets_id_seq' next_value type is 'bigint' ==> max value = 9223372036854775807
-- With one unique sequence, and after a number of new table creations and insertion in these tables, new insertions in dns_packets_*' tables become impossible.

CREATE OR REPLACE FUNCTION partitioning2() RETURNS TRIGGER AS $trg_partitioning2$
    DECLARE
        table_name TEXT = 'dns_packets_' || NEW.id;
        sequence_name TEXT = 'dns_packets_' || NEW.id || '_id_seq';
    BEGIN
        EXECUTE 'CREATE TABLE ' || table_name || ' (check (file = ' || NEW.id ||')) INHERITS (dns_packets);';
		EXECUTE 'CREATE SEQUENCE ' || sequence_name || ' INCREMENT BY 1 START WITH 1 CACHE 1 NO CYCLE;';
		EXECUTE 'ALTER TABLE ' || table_name || ' ALTER COLUMN id SET default nextval(''' || sequence_name || ''');';
        RETURN NEW;
    END;
$trg_partitioning2$ LANGUAGE plpgsql;

CREATE TRIGGER trg_partitioning2 AFTER INSERT ON pcap_files
    FOR EACH ROW EXECUTE PROCEDURE partitioning2();



-- Examples of requests:
-- Hint: To take advantage of partitioning (and so to boost performances significantly), add 'WHERE file = ' conditions.
-- (on postgresql < 8.4, you also need to run 'SET constraint_exclusion = true;')
--
-- 1) to find the NXDOMAIN (rcode 3) responses:
-- SELECT DISTINCT substr(qname, 1, 40) AS domain,count(qname) AS num FROM DNS_packets WHERE NOT query AND rcode= 3 GROUP BY qname ORDER BY count(qname) DESC;
--
-- 2) to find the most talkative IPv6 clients
-- SELECT src_address,count(src_address) AS requests FROM DNS_packets WHERE family(src_address)=6 AND query GROUP BY src_address ORDER BY requests DESC;
--
-- 3) to find the typical EDNS0 sizes advertised by clients
-- SELECT edns0_size, count(edns0_size) AS occurrences FROM DNS_packets WHERE query GROUP BY edns0_size ORDER BY occurrences DESC;

