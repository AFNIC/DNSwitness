CREATE OR REPLACE FUNCTION first_label(TEXT) RETURNS TEXT IMMUTABLE AS
   '
     DECLARE
       first_dot INTEGER;
     BEGIN
       first_dot = strpos($1, ''.'');
       RETURN substr($1, 1, first_dot-1);
     END;
   '
 LANGUAGE PLPGSQL;

CREATE OR REPLACE FUNCTION last_labels(TEXT, INTEGER) RETURNS TEXT IMMUTABLE AS
   '
     DECLARE
       next_dot INTEGER;
       index INTEGER;
       subsets TEXT[];
       rest TEXT;
     BEGIN
       index = 1;
       rest = $1;
       next_dot = strpos(rest, ''.'');
       IF next_dot = 0 THEN
          subsets[0] = rest;
       END IF;
       WHILE next_dot != 0 LOOP
          rest = substr(rest, next_dot+1);
          subsets[index] = rest;
          index = index + 1;
          next_dot = strpos(rest, ''.'');
       END LOOP;
       IF index <= $2 THEN
          RETURN $1;
       ELSE
          RETURN subsets[index-$2];
       END IF;
     END;
   '
 LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION last_label(TEXT) RETURNS TEXT IMMUTABLE AS
   '
     DECLARE
       first_dot INTEGER;
       rest TEXT;
     BEGIN
       first_dot = strpos($1, ''.'');
       rest = substr($1, first_dot+1);
       IF strpos(rest, ''.'') = 0 THEN
          RETURN rest;
       ELSE
          RETURN last_label(rest);
       END IF;
     END;
   '
 LANGUAGE PLPGSQL;


-- SELECT first_label('foobar.sub.nic.fr');
-- SELECT last_label('foobar.sub.nic.fr');
-- SELECT last_labels('foobar.sub.nic.fr', 3);

-- Top domains:
-- SELECT last_labels(qname, 2) AS domain,count(id) AS packets FROM DNS_packets GROUP BY domain ORDER BY packets DESC;
-- Top Conficker domains:
-- SELECT last_labels(qname, 2) AS domain,count(id) AS packets FROM DNS_packets WHERE last_labels(qname, 2) IN (SELECT name FROM Conficker.CandC_domains) GROUP BY domain ORDER BY packets DESC;
