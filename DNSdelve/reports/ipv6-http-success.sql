-- OK, they have a AAAA record for the Web. But does it work?

SELECT count(*) FROM hosts WHERE uuid='edd18db4-0898-41f7-bbe8-40cef52f91aa' AND 
     service='HTTP' AND result;

SELECT count(*) FROM hosts WHERE uuid='edd18db4-0898-41f7-bbe8-40cef52f91aa' AND 
     service='HTTP' AND NOT result;