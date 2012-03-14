DROP TABLE Crossed_redirections;
DROP TABLE Crossed_ns;
DROP TABLE ASN;
DROP TABLE Redirect;
DROP TABLE URI;

\i runs-create.sql

CREATE TABLE URI (
        id SERIAL UNIQUE NOT NULL,
        uri TEXT UNIQUE NOT NULL,
        authority TEXT,
        reg_dom TEXT,
        tld TEXT
        );

CREATE TABLE Redirect (
        id SERIAL UNIQUE NOT NULL,
        uuid UUID NOT NULL,
        orig SERIAL REFERENCES URI(id),
        target SERIAL REFERENCES URI(id),
        UNIQUE (uuid, orig, target)
        );

ALTER TABLE Redirect ALTER COLUMN target DROP NOT NULL;

CREATE TABLE Crossed_redirections (
        id SERIAL UNIQUE NOT NULL,
        id_redirect SERIAL NOT NULL REFERENCES Redirect(id),
        type TEXT NOT NULL,
        origin SERIAL REFERENCES URI(id),
        target SERIAL REFERENCES URI(id)
        );

CREATE TABLE Crossed_ns (
        id SERIAL UNIQUE NOT NULL,
        uuid UUID NOT NULL,
        authority TEXT NOT NULL,
        id_ns SERIAL REFERENCES URI(id),
        UNIQUE (uuid, authority, id_ns)
        ); -- TODO Ensure integrity by testing if authority exist somewhere in URI (and with uuid) -> add a trigger on insert?

CREATE TABLE ASN (
        id SERIAL UNIQUE NOT NULL,
        uuid UUID NOT NULL,
        authority TEXT,
        asn INTEGER NOT NULL,
        UNIQUE (uuid, authority, asn)
        ); -- TODO same as above

-- We use explicit locks in this functions.
-- There were deadlocks when relying on exceptions handling.
CREATE OR REPLACE FUNCTION store_uri (p_uri TEXT,
                                      p_authority TEXT,
                                      p_reg_dom TEXT,
                                      p_tld TEXT)
RETURNS INTEGER AS $$
DECLARE
    id_uri INTEGER;
    authority TEXT := NULL;
    reg_dom TEXT := NULL;
    tld TEXT := NULL;
BEGIN

    IF p_authority != '' THEN -- Bad redirection ?
        authority := p_authority;
    END IF;
    IF p_reg_dom != '' THEN -- IP
        reg_dom := p_reg_dom;
    END IF;
    IF p_tld != '' THEN
        tld := p_tld;
    END IF;

    LOCK TABLE URI IN ACCESS EXCLUSIVE MODE;

    SELECT id INTO id_uri FROM URI u WHERE u.uri = p_uri;
    IF id_uri IS NULL THEN
        SELECT nextval('uri_id_seq') INTO id_uri;
        INSERT INTO URI VALUES (id_uri, p_uri, authority, reg_dom, tld);
    END IF;
    RETURN id_uri;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION store_asn (p_uuid UUID,
                                      p_domain TEXT,
                                      p_asn TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    t_asn TEXT[];
    id_asn INTEGER;
BEGIN

    IF p_asn != '' THEN
        LOCK TABLE ASN IN ACCESS EXCLUSIVE MODE;

        SELECT regexp_split_to_array(p_asn, E'\\|') INTO t_asn;
        FOR i IN 1..array_length(t_asn, 1) LOOP
            SELECT id INTO id_asn FROM ASN a WHERE a.uuid = p_uuid AND a.authority = p_domain AND a.asn = t_asn[i]::INTEGER;
            IF id_asn IS NULL THEN
                INSERT INTO ASN (uuid, authority, asn) VALUES (p_uuid, p_domain, t_asn[i]::INTEGER);
            END IF;
        END LOOP;
    END IF;
    RETURN 't';
END;
$$LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION store_crossed_ns (p_uuid UUID,
                                             p_auth TEXT,
                                             p_ns INTEGER[])
RETURNS BOOLEAN AS $$
DECLARE
    id_cns INTEGER;
BEGIN
    LOCK Crossed_ns IN ACCESS EXCLUSIVE MODE;
    FOR i IN 1..array_length(p_ns, 1) LOOP
        SELECT id INTO id_cns FROM Crossed_ns WHERE uuid = p_uuid AND authority = p_auth AND id_ns = p_ns[i];
        IF id_cns IS NULL THEN
            INSERT INTO Crossed_ns (uuid, authority, id_ns) VALUES (p_uuid, p_auth, p_ns[i]);
        END IF;
    END LOOP;
    RETURN 't';
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION store (p_uuid UUID,
                                  p_ori TEXT,
                                  p_auth TEXT,
                                  p_reg_dom TEXT,
                                  p_tld TEXT,
                                  p_asn TEXT,
                                  p_target TEXT,
                                  p_target_auth TEXT,
                                  p_target_rd TEXT,
                                  p_target_tld TEXT,
                                  p_target_asn TEXT,
                                  p_cr TEXT[][])
RETURNS BOOLEAN AS $$
DECLARE
    id_redir INTEGER;
    id_origin INTEGER;
    id_target INTEGER := NULL;
    r_id_cr INTEGER;
BEGIN
    SELECT store_uri(p_ori, p_auth, p_reg_dom, p_tld) INTO id_origin;
    PERFORM store_asn(p_uuid, p_auth, p_asn);

    IF p_target IS NOT NULL THEN
        SELECT store_uri(p_target, p_target_auth, p_target_rd, p_target_tld) INTO id_target;
        PERFORM store_asn(p_uuid, p_target_auth, p_target_asn);
    END IF;

    INSERT INTO Redirect VALUES (DEFAULT, p_uuid, id_origin, id_target) RETURNING id INTO id_redir;

    IF array_length(p_cr, 1) != 0 THEN
        FOR i IN 1..array_length(p_cr, 1) LOOP
            SELECT store_uri(p_cr[i][2], p_cr[i][3], p_cr[i][4], p_cr[i][5]) INTO id_origin;
            PERFORM store_asn(p_uuid, p_cr[i][3], p_cr[i][6]);

            IF p_cr[i][7] IS NOT NULL THEN
                SELECT store_uri(p_cr[i][7], p_cr[i][8], p_cr[i][9], p_cr[i][10]) INTO id_target;
                PERFORM store_asn(p_uuid, p_cr[i][8], p_cr[i][11]);
            ELSE
                id_target := NULL;
            END IF;

            INSERT INTO Crossed_redirections (id_redirect, type, origin, target) VALUES (id_redir, p_cr[i][1], id_origin, id_target);

        END LOOP;
    END IF;
    RETURN 't';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION store_ns (p_uuid UUID,
                                     p_domain TEXT,
                                     p_ns TEXT[][])
RETURNS BOOLEAN AS $$
DECLARE
    id_uri INTEGER;
    id_cns INTEGER[];
BEGIN

    FOR i IN 1..array_length(p_ns, 1) LOOP
        SELECT store_uri(p_ns[i][1], p_ns[i][2], p_ns[i][3], p_ns[i][4]) INTO id_uri;
        id_cns[i] := id_uri;
        PERFORM store_asn(p_uuid, p_ns[i][2], p_ns[i][5]);
    END LOOP;
    PERFORM store_crossed_ns(p_uuid, p_domain, id_cns);
    RETURN 't';
END;
$$ LANGUAGE plpgsql;

