SELECT domain,aaaa_ns FROM v6_dns WHERE 
     uuid='23a4933e-0d11-4fa9-8e4a-602ba3c8373d' AND 
     domain NOT IN 
         (SELECT domain from v6_dns WHERE 
             uuid='5dd11814-f1d3-4c61-9c04-1d2170787e5e');
