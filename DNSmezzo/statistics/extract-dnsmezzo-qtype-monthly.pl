#!/usr/bin/perl

use strict;

use DBI;
use Getopt::Long;

my $debug = 2;

my $database = 'dbi:Pg:dbname=' . 'dnsmezzo';
my $user     = 'dnsmezzo';

### $probe_reg = 'mezzo\-dns\.(fra.nic.fr-d.nic.fr)\-dns\-SAMPLING';
my $probe_reg = 'mezzo\-dns\.(.*)\-dns\-SAMPLING';

#####################  
## Read line options
#####################

my %opts;
my $reason;
 


GetOptions(\%opts, "help|h", "debug|d:i", "start|t:s", "stop|p:s", "all_probes|a", "probe|s:s" );

if ( exists $opts{'help'} ) {
	usage();
	die(0);
}

if ( exists $opts{'all_probes'} and exists $opts{'probe'} ) {
	$reason = q{options 'all_probes' and 'probe' are exclusive};
	usage();
	die($reason);
}

if ( exists $opts{'debug'} ) { 
	$debug = $opts{'debug'}; 
} else {
	$debug = 2;
}

if ( exists $opts{'start'} ) {   
	unless ( $opts{'start'} =~ m!^\d{4}\-\d{2}$! ){
		$reason = "start time format must be YYYY-MM";
		usage();
		die($reason);
	} 
} else {
	$opts{'start'} = Default_Start();
}

if ( exists $opts{'stop'} ) {
	unless ( $opts{'stop'} =~ m!^\d{4}\-\d{2}$! ){
		$reason = "stop time format must be YYYY-MM";
		usage();
		die($reason);
	} 
} else {
	$opts{'stop'} = Default_Stop();
}

if ( exists $opts{'probe'} ) {
	$opts{'all_probes'} = 0;	
} else {
	$opts{'all_probes'} = 1;	
}


###############################
## Launch stats gathering
###############################

my @now = localtime(time());
my $file_suffixe = sprintf "%d%02d%02d-%02d%02d", $now[5] + 1900, $now[4] + 1, $now[3], $now[2], $now[1]; 
my $file_prefixe = 'stats-dnsmezzo-qtype'; 

my %Stats = ();
my %GlobalStats = ();

my $dbh = DBI->connect($database, $user ) or die "cannot open $database $DBI::errstr \nThis script must be run by $user !!";

#############
## Get dns_packets tables from pcap_files table
#############

my $start_date = $opts{'start'} . '-01';
my $stop_date  = $opts{'stop'} . '-01';

my $probe_filter = '';

if ( $opts{'all_probes'} == 0 ) {
	$probe_filter = qq{ and filename like '%dns.$opts{"probe"}' };
}

my $sql = qq{ 
	select id, date_trunc('month',firstpacket) , filename  
	from pcap_files
	where firstpacket >= DATE('$start_date') and firstpacket < DATE('$stop_date') 
	and filename like '%mezzo-dns%'
	$probe_filter 
	order by id
};

print "executing : $sql .... \n\n" if ($debug >= 1);
my $sth = $dbh->prepare($sql);
$sth->execute();

my %Probes = ();
my ($probe, $month, @row) ;

while ( @row = $sth->fetchrow_array() ) {

	print "$row[0] - $row[1] - $row[2] " if ($debug >= 3);

	($probe) = ( $row[2] =~ m!$probe_reg! );
	$month   =  $row[1]; 
	$month   =~ s!^(\d{4})\-(\d{2}).*$!$1\-$2! ;
	print " ===> $month *$probe* \n" if ($debug >= 3);

	unless ( exists $Probes{$probe}{$month} ) { $Probes{$probe}{$month} = []; };
	push @{$Probes{$probe}{$month}}, $row[0];
}


foreach $probe ( keys %Probes ) {

	GetProbeStats($probe);
}

PrintGlobalStats();

$dbh->disconnect();







#######################
## usage
#######################

sub usage {

	print qq {
usage :  get_ipv6_dnsmezzo.pl [--start|-t start_month] [--stop|-p stop_month] [--probe|-s probe] [--all_probes|-a]
   where start_month, stop_month formats are YYYY-MM
   and probe in ('bru', 'th2', 'lyn1', 'fra' ...)

};

}
######################
## Default_Start
######################

sub Default_Start {

	## If today is 2012-12-06 ==> Default_Start = 2011-01

	my ($mon, $year) = (localtime(time))[4,5];
	$year += 1900;
	$mon = 1;

	$year = $year -1 ; # start 1 year ago
	$mon  = 1;         # start from january 

	return sprintf ("%d-%02d", $year, $mon);

}



######################
## Default_Stop
######################

sub Default_Stop {

	## If today is 2012-12-06 ==> Default_Start = 2013-01

	my ($mon, $year) = (localtime(time))[4,5];
	$year += 1900;
	$mon += 1;  # normal reformatting

	$mon += 1;	# we'll stop at the end of the current month (so 1st day of next month)
	if ( $mon == 13 ) {
		$mon = 1;
		$year += 1;
	}
	return sprintf ("%d-%02d", $year, $mon);
}




################################
## GetProbeStats
################################

sub GetProbeStats {

	my $probe = shift;

	print "Probe $probe ... \n" if ($debug >= 1);

	my ($table, @tables,$tsql, @Sql, @Stats, @months, $month, @counts);
	my ($total, $measures);
	my ($qa, $qb, $qc, $qd, $qe, $qf, $qg, $qh, $qi, $qj, $qk);


	## DNS queries made with IPv6 transport
	$Sql[0] = 'select count(id) from table  where query and family(src_address)=6';
	## DNS queries for qtype AAAA 
	$Sql[1] = 'select count(id) from table  where query and qtype=28';
	## DNS queries for qtype A 
	$Sql[2] = 'select count(id) from table  where query and qtype=1';
	## DNS queries for qtype A6
	$Sql[3] = 'select count(id) from table  where query and qtype=38';
	## DNS queries for qtype MX
	$Sql[4] = 'select count(id) from table  where query and qtype=15';
	## DNS queries for qtype NS
	$Sql[5] = 'select count(id) from table  where query and qtype=2';
	## DNS queries for qtype TXT
	$Sql[6] = 'select count(id) from table  where query and qtype=16';
	## DNS queries for qtype DS
	$Sql[7] = 'select count(id) from table  where query and qtype=43';
	## DNS queries for qtype DNSKEY
	$Sql[8] = 'select count(id) from table  where query and qtype=48';
	## DNS queries for qtype ANY
	$Sql[9] = 'select count(id) from table  where query and qtype=255';

	## ALL queries      !!!!  REMEMBER : let total queries as the last element of Sql array
	$Sql[10] = 'select count(id) from table  where query ';

	my $file  = $file_prefixe . '_' . $probe . '_' . $file_suffixe . '.txt'; 
	open(FILE, ">$file");

	print FILE "#---------------------------------- \n";
	print FILE "# Statistiques pour la sonde $probe \n";
	print FILE "#---------------------------------- \n";
	print FILE "# Mois ; Nombre de mesures ; Transport IPv6 (*) ; AAAA (*) ;  A (*) ; A6(*) ; MX(*) ; NS(*) ; TXT(*) ; DS(*), DNSKEY(*), ANY(*) ; Nombre total de requetes (**)\n";
	print FILE "#    (*)  : requetes de ce type en % du nombre de requetes total \n";
	print FILE "#    (**) : moyenne du nombre total de requetes par mesure \n";

	my @months = keys %{$Probes{$probe}};
	@months = sort { $a cmp $b } @months;

	foreach $month (@months) {

		@tables =  @{$Probes{$probe}{$month}};	
		@tables = map { 'dns_packets_' . $_ } @tables;

		$measures = 0;

		for $table ( @tables ) {

			$measures += 1;
			print "\t\t $table \n" if ($debug >= 2);

			@counts = ();
			my ($i, $j, $sth);

			for ( $i =0 ; $i < scalar(@Sql) ; $i++) {

				$tsql = $Sql[$i]; 
				$tsql =~ s!table!$table!;
				$sth  = $dbh->prepare($tsql);
				$sth->execute();
				( $counts[$i] ) = $sth->fetchrow_array(); 
				$sth->finish();
			}

			$total = $counts[$#Sql];

			$Stats{$probe}{$month}{'v6_transport'} += $counts[0] / $total;
			$Stats{$probe}{$month}{'aaaa_query'}   += $counts[1] / $total;
			$Stats{$probe}{$month}{'a_query'}      += $counts[2] / $total;
			$Stats{$probe}{$month}{'a6_query'}     += $counts[3] / $total;
			$Stats{$probe}{$month}{'mx_query'}     += $counts[4] / $total;
			$Stats{$probe}{$month}{'ns_query'}     += $counts[5] / $total;
			$Stats{$probe}{$month}{'txt_query'}    += $counts[6] / $total;
			$Stats{$probe}{$month}{'ds_query'}     += $counts[7] / $total;
			$Stats{$probe}{$month}{'dnskey_query'} += $counts[8] / $total;
			$Stats{$probe}{$month}{'any_query'}    += $counts[9] / $total;
			$Stats{$probe}{$month}{'total_query'}  +=  $total;
		}

		$qa = $Stats{$probe}{$month}{'v6_transport'}  = $Stats{$probe}{$month}{'v6_transport'} / $measures * 100 ;
		$qb = $Stats{$probe}{$month}{'aaaa_query'}    = $Stats{$probe}{$month}{'aaaa_query'}   / $measures * 100 ;
		$qc = $Stats{$probe}{$month}{'a_query'}       = $Stats{$probe}{$month}{'a_query'}      / $measures * 100 ;
		$qd = $Stats{$probe}{$month}{'a6_query'}      = $Stats{$probe}{$month}{'a6_query'}     / $measures * 100 ;
		$qe = $Stats{$probe}{$month}{'mx_query'}      = $Stats{$probe}{$month}{'mx_query'}     / $measures * 100 ;
		$qf = $Stats{$probe}{$month}{'ns_query'}      = $Stats{$probe}{$month}{'ns_query'}     / $measures * 100 ;
		$qg = $Stats{$probe}{$month}{'txt_query'}     = $Stats{$probe}{$month}{'txt_query'}    / $measures * 100 ;
		$qh = $Stats{$probe}{$month}{'ds_query'}      = $Stats{$probe}{$month}{'ds_query'}     / $measures * 100 ;
		$qi = $Stats{$probe}{$month}{'dnskey_query'}  = $Stats{$probe}{$month}{'dnskey_query'} / $measures * 100 ;
		$qj = $Stats{$probe}{$month}{'any_query'}     = $Stats{$probe}{$month}{'any_query'}    / $measures * 100 ;
		$qk = $Stats{$probe}{$month}{'total_query'}   = $Stats{$probe}{$month}{'total_query'} / $measures ;

		printf FILE "$month ; %4d mesures  ; %02.2f ; %02.2f ; %02.2f ; %02.2f ; %02.2f ; %02.2f ;%02.2f ; %02.2f ; %02.2f ; %02.2f ; %d \n", $measures, $qa,$qb,$qc,$qd,$qe,$qf,$qg,$qh,$qi,$qj,$qk ;

		unless ( exists $GlobalStats{$month} ) {
		
			$GlobalStats{$month}{'nb_probes'}    = 0;
			$GlobalStats{$month}{'v6_transport'} = 0;
			$GlobalStats{$month}{'aaaa_query'}   = 0;
			$GlobalStats{$month}{'a_query'}      = 0;
			$GlobalStats{$month}{'a6_query'}     = 0;
			$GlobalStats{$month}{'mx_query'}     = 0;
			$GlobalStats{$month}{'ns_query'}     = 0;
			$GlobalStats{$month}{'txt_query'}    = 0;
			$GlobalStats{$month}{'ds_query'}     = 0;
			$GlobalStats{$month}{'dnskey_query'} = 0;
			$GlobalStats{$month}{'any_query'}    = 0;
			$GlobalStats{$month}{'total_query'}  = 0;
		}
		
		$GlobalStats{$month}{'nb_probes'}    += 1;
		$GlobalStats{$month}{'v6_transport'} += $qa;
		$GlobalStats{$month}{'aaaa_query'}   += $qb;
		$GlobalStats{$month}{'a_query'}      += $qc;
		$GlobalStats{$month}{'a6_query'}     += $qd;
		$GlobalStats{$month}{'mx_query'}     += $qe;
		$GlobalStats{$month}{'ns_query'}     += $qf;
		$GlobalStats{$month}{'txt_query'}    += $qg;
		$GlobalStats{$month}{'ds_query'}     += $qh;
		$GlobalStats{$month}{'dnskey_query'} += $qi;
		$GlobalStats{$month}{'any_query'}    += $qj;
		$GlobalStats{$month}{'total_query'}  += $qk;


	}

	close FILE;

}


################################
## PrintGlobalStats
################################

sub PrintGlobalStats {


	my $file  = $file_prefixe . '_' . 'all-probes' . '_' . $file_suffixe . '.txt'; 

	open(FILE, ">$file");

	print FILE "#--------------------------------------------- \n";
	print FILE "# Statistiques globales pour toutes les sondes \n";
	print FILE "#--------------------------------------------- \n";
	print FILE "# Mois ; Nombre de sondes ; Transport IPv6 (*) ; AAAA (*) ;  A (*) ; A6(*) ; MX(*) ; NS(*) ; TXT(*) ; DS(*) ; DNSKEY(*) ; ANY(*) ; Nombre total de requetes (**)\n";
	print FILE "#    (*)  : requetes de ce type en % du nombre de requetes total \n";
	print FILE "#    (**) : moyenne du nombre total de requetes par mesure et par sonde \n\n";


	my ($month, @months, $qn, $qa, $qb, $qc, $qd, $qe, $qf, $qg, $qh, $qi, $qj, $qk);


	@months = sort { $a cmp $b } ( keys %GlobalStats );

	foreach $month ( @months ) {

		$qn = $GlobalStats{$month}{'nb_probes'}; 
		$qa = $GlobalStats{$month}{'v6_transport'} / $qn ;
		$qb = $GlobalStats{$month}{'aaaa_query'}   / $qn ;
		$qc = $GlobalStats{$month}{'a_query'}      / $qn ;
		$qd = $GlobalStats{$month}{'a6_query'}     / $qn ;
		$qe = $GlobalStats{$month}{'mx_query'}     / $qn ;
		$qf = $GlobalStats{$month}{'ns_query'}     / $qn ;
		$qg = $GlobalStats{$month}{'txt_query'}    / $qn ;
		$qh = $GlobalStats{$month}{'ds_query'}     / $qn ;
		$qi = $GlobalStats{$month}{'dnskey_query'} / $qn ;
		$qj = $GlobalStats{$month}{'any_query'}    / $qn ;
		$qk = $GlobalStats{$month}{'total_query'}  / $qn ;

		printf FILE "$month ; %4d sondes ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %2.2f ; %d \n", $qn, $qa,$qb,$qc,$qd,$qe,$qf,$qg,$qh,$qi,$qj,$qk ;
	}

	close FILE;
}
