-- Domains tested
select count(distinct zones.zone) from broker,zones where broker.uuid='b0cc6bb3-2777-48a2-858f-f468e6e0280e' and broker.zone=zones.id ;

-- Domains with a MX
select count(distinct zones.zone) from broker,zones where broker.uuid='7c7de81d-81ad-4725-9df6-3756e4c6dd01' and broker.zone=zones.id and broker.id in (select broker from Tests_mx_zone);

-- Domains with a working SMTP server
select count(distinct zones.zone) from broker,zones where broker.uuid='7c7de81d-81ad-4725-9df6-3756e4c6dd01' and broker.zone=zones.id  and broker.id in (select broker from Tests_mx_zone where Tests_mx_zone.result) ;
