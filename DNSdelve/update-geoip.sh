#!/bin/sh
# Script to update GeoIP binary databases.
# You may prefer the package provided by your favourite OS (eg. the "geoip-database" package is updated quite often on Debian)

cd /usr/share/GeoIP
wget http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz
wget http://geolite.maxmind.com/download/geoip/database/GeoIPv6.dat.gz
gzip -d -f GeoIP.dat.gz
gzip -d -f GeoIPv6.dat.gz
