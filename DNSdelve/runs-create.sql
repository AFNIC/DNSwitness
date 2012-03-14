DROP TABLE Runs;

CREATE TABLE Runs (id SERIAL UNIQUE NOT NULL,
       uuid UUID UNIQUE NOT NULL,
       date TIMESTAMP NOT NULL DEFAULT now(),
       module TEXT NOT NULL,
       zonefile TEXT,
       numberdomains INTEGER CHECK (numberdomains > 0), -- Number of domains actually surveyed
       totaldomains INTEGER CHECK (totaldomains > 0), -- Number of domains in zonefile
       samplingrate FLOAT CHECK (samplingrate <= 1.0 AND samplingrate >= 0.0));


