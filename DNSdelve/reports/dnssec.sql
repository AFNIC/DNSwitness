SELECT count(*) FROM zones z, tests t WHERE z.id=t.zone AND 
     t.uuid='49030d6d-e61d-409e-bddc-27df7f18f23b' AND t.dnskey;

