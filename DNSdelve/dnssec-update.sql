-- Update an old dnssec DB (to query dns keys)

CREATE TABLE keys (id SERIAL UNIQUE NOT NULL,
       keyid INTEGER NOT NULL,
       algorithm INTEGER NOT NULL,
       keylength INTEGER,
       key TEXT NOT NULL,
       PRIMARY KEY (id));

CREATE TABLE tests_keys (id_test SERIAL NOT NULL REFERENCES tests(id),
       id_key SERIAL NOT NULL REFERENCES keys(id));


-- You need to install the plpgsql language:
-- http://www.postgresql.org/docs/8.1/static/xplang.html
CREATE OR REPLACE FUNCTION insert_dnssec (p_uuid UUID,
                  p_domain TEXT,
                  p_keyid INTEGER,
                  p_algorithm INTEGER,
                  p_keylength INTEGER,
                  p_key TEXT)
RETURNS BOOLEAN AS $$
DECLARE
key_id INTEGER;
test_id INTEGER;
BEGIN

    SELECT id INTO key_id FROM keys k WHERE k.key = p_key;

    IF key_id IS NULL THEN
        SELECT nextval('keys_id_seq') INTO key_id;
        INSERT INTO keys (id, keyid, algorithm, keylength, key)
        VALUES (key_id, p_keyid, p_algorithm, p_keylength, p_key);
    END IF;

    SELECT id INTO test_id FROM tests t WHERE t.uuid = p_uuid AND t.domain = p_domain;

    INSERT INTO tests_keys (id_test, id_key) VALUES (test_id, key_id);

    RETURN (TRUE);
END;
$$ LANGUAGE plpgsql;
