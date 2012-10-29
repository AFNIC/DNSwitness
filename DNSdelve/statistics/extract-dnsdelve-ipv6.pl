#!/usr/bin/perl

use strict;
use Env qw(USER);
use DBI;


my $debug    = 1;
my $database = 'dbi:Pg:dbname=' . 'dnsdelve-ip';
my $user     = $USER;
my $passwd   = '';

my %Stats = ();
my %Counts = ();
my $at;

$at = now();
print "Starting IPv6 data extraction at $at ... \n" if ($debug >= 1);

my @Sql = (
	'select uuid, id, zone from v6_dns', 
	'select uuid, id, zone from v6_email', 
	'select uuid, id, zone from v6_web', 
	'select uuid, id, zone from v6_enabled', 
	'select uuid, id, zone from v6_full', 
);


my @TotalSql = (
	'select t.broker, b.uuid from tests_ns_zone t, broker b where t.broker=b.id', 
	'select t.broker, b.uuid from tests_mx_zone t, broker b where t.broker=b.id', 
	'(select t.broker, b.uuid from tests_www_zone t, broker b where t.broker=b.id) 
	   UNION (select t.broker, b.uuid from tests_www_ipv6_zone t, broker b where t.broker=b.id) 
	   UNION (select t.broker, b.uuid from tests_zone t, broker b where t.broker=b.id)', 
	'select t.broker, b.uuid from tests t, broker b where t.broker=b.id', 
	'select t.broker, b.uuid from tests t, broker b where t.broker=b.id', 
);


my $dbh = DBI->connect($database, $user, $passwd) or die "cannot open $database $DBI::errstr \n";

for (my $i=0; $i < scalar(@Sql) ; $i++ ) {
	GetDatafromView($i);
	GetTotalTests($i);
}


PrintGlobalStats();

$dbh->disconnect();



################################
## GetDatafromView
################################

sub GetDatafromView {

	my $i = shift;

	my @row;
	my $string;

	my $sql = $Sql[$i];

	my $table = (split ' ', $sql)[-1];
	my $file  = time() . '-' . $table . '.tmp' ;
	open(FILE, ">$file") if ( $debug >= 2);

	$at = now();	
	print "Getting Ipv6 data for $table at $at ...\n" if ($debug >= 1);

	$Stats{$table} = {};

	my $sth = $dbh->prepare($sql);
	$sth->execute();

	while ( @row = $sth->fetchrow_array() ) {

		if ( $debug >= 2 ) {
			$string = join ('; ', @row);
			print FILE "$string \n";
		}

		$Stats{$table}{$row[0]} += 1;    # stats IPv6 by type and by uuid
	}

	close FILE if ($debug >= 2);

}

################################
## GetTotalTests
################################

sub  GetTotalTests {

	my $i = shift;

	my $table = $Sql[$i];
	$table = (split ' ', $table)[-1];

	$at = now();
	print "Getting tests total count for $table at $at ...\n" if ($debug >= 1);

	my ($broker, $uuid);
	my $sql = $TotalSql[$i];

	my $sth = $dbh->prepare($sql);
	$sth->execute();

	my %Seen = ();

	while ( ($broker, $uuid) = $sth->fetchrow_array() ) {

		unless ( $Seen{$broker} ) {
			$Counts{$table}{$uuid} += 1;
			$Seen{$broker} = 1;
		}
	}


	if ( $debug >=2 ) {
		my $file  = time() . '-' . $table . '-uuid.tmp' ;
		open(FILE, ">$file"); 
		foreach my $uuid (keys %{$Counts{$table}} ) {
			print FILE "$uuid - $Counts{$table}{$uuid} \n";
		}
		close FILE;
	}

}



################################
## PrintGlobalStats
################################

sub PrintGlobalStats {

	$at = now();
	print "Re-ordering results by month at $at ...\n" if ($debug >= 1);

	my ($t_year, $t_month, $t_day, $t_hour, $t_min) = (localtime(time))[5,4,3,2,1];
	$t_year += 1900;
	$t_month += 1;
	$t_month = sprintf '%02d', $t_month;
	$t_day   = sprintf '%02d', $t_day;
	$t_hour  = sprintf '%02d', $t_hour;
	$t_min   = sprintf '%02d', $t_min;

	my $mfile = 'stats-dnsdelve-ipv6-' . $t_year . $t_month . $t_day . '-' . $t_hour . $t_min . '.txt';
	open(MFILE, ">$mfile");

	my $file = time() . '-' . 'global_stats.tmp';
	open(FILE, ">$file") if ($debug >= 2) ;

	my %StatByMonth = ();
	my ($k, $u, $n, $f, $p, $month, $date, $s, $T );

	my $sql1 = "select date, numberdomains, samplingrate from runs where uuid=?";
	my $sth1 = $dbh->prepare($sql1);

	foreach $k (keys %Stats ) {

		if ( $debug >= 2 ) {

			print FILE "####################\n";
			print FILE "#  Table $k \n";
			print FILE "####################\n";
		}

		$at = now();	
		print "Re-ordering results for $k at $at ...\n" if ($debug >= 1);

		$StatByMonth{$k} = {};

		my @Uuid = sort { $a <=> $b } ( keys %{$Stats{$k}} );  # sort by uuid ascending

		## Get corresponding run date + meta-data

		foreach $u ( @Uuid ) {

			$sth1->execute($u);
			($date, $n, $s ) = $sth1->fetchrow_array();

			$T = $Counts{$k}{$u} ;

			if ( $T ) {
				$f =  $Stats{$k}{$u} / $T * 100 ;
				$p = sprintf "%3.2f", $f ;
			} else {
				$f =  0;
				$p = 'undef' ;
				print STDERR "No total count fo uuid = $u \n";
			}

			print FILE "$date - $n - $Stats{$k}{$u} ($p) \n" if ($debug >= 2) ;

			($month) =  ( $date =~ m!^(\d{4}-\d{2})! );

			unless ( exists $StatByMonth{$k}{$month} ) {
				$StatByMonth{$k}{$month}{'avg'}  = 0; 
				$StatByMonth{$k}{$month}{'zone'} = 0 
			} 
			$StatByMonth{$k}{$month}{'avg'} += $f; 
			$StatByMonth{$k}{$month}{'runs'} += 1; 
			$StatByMonth{$k}{$month}{'zone'} += int($n / $s); 
			
		}

		my @Months = sort { $a cmp $b } ( keys %{$StatByMonth{$k}} );	

		print MFILE "####################\n";
		print MFILE "#  Domaines $k \n";
		print MFILE "####################\n";
		print MFILE "# Mois ; Nombre moyen de noms de domaines (*) ; Taille moyenne de la zone fr \n";
		print MFILE "#    (*) domaines repondant au critere de selection Ipv6 \n\n";

		foreach $month ( @Months ) {
			
			printf MFILE "%s ; %3.2f ; %d \n", $month, $StatByMonth{$k}{$month}{'avg'} / $StatByMonth{$k}{$month}{'runs'} , $StatByMonth{$k}{$month}{'zone'} / $StatByMonth{$k}{$month}{'runs'};
			
		}
		

	}

	close FILE if ($debug >= 2);
	close MFILE;
}


sub now {

	my ($hour, $min, $sec) = (localtime(time))[2,1,0];
	return sprintf "%02d:%02d:%02d",$hour, $min, $sec;

}
