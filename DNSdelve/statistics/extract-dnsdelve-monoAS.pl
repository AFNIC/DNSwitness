#!/usr/bin/perl

use strict;
use DBI;
use vars qw ( @ARGV );
use Getopt::Long;  
use File::Basename;
use File::Open qw(fopen);
use Data::Dumper;

our $Name = 'extract-dnsdelve-topology';

our $database = 'dbi:Pg:' . 'dbname=dnsdelve-ip';
our $user   = '';
our $passwd = '';
our $dbh;
our $at;

our %opts;
our %Stats;

use constant START_DATE => '2011-08-01';  #Details about DNS servers were not stored in db, before this date.

MAIN: {

	#--------------------------
	# read command line options
	#---------------------------

	my $msg;


	GetOptions(\%opts, "help|h", "debug|d:i", "all_runs|a", "one_run|r:s", "one_month|m:s", "output|o:s");

	if ( $opts{'help'} ) {
		usage();
		exit(0);
	}

	if ( ( exists $opts{'all_runs'} and exists $opts{'one_run'}   ) or
     	 ( exists $opts{'all_runs'} and exists $opts{'one_month'} ) or 
		 ( exists $opts{'one_run'}  and exists $opts{'one_month'} ) ) {

		$msg = q{options 'all_runs', 'one_run', 'one_month' are exclusive};
		usage($msg);
		exit(0);
	}

	if ( exists $opts{'one_month'} and ( $opts{'one_month'} !~ m!^\d{4}\-?\d{2}$! )) {
		$msg = q{ option 'one_month' format must be YYYY-MM or YYYYMM };
		usage($msg);
		exit(0);
	}

	if ( exists $opts{'one_run'} or exists $opts{'one_month'} ) {
		$opts{'all_runs'} = 0;
	}

	#------------------
	# Default options
	#------------------
	unless (exists $opts{'debug'}) {
		$opts{'debug'}   = 1;
	}
	unless ( exists $opts{'all_runs'} or exists $opts{'one_run'} or exists $opts{'one_month'} ) {
		$opts{'all_runs'} = 1;
	}
	if ( exists $opts{'one_month'} ) {
		$opts{'one_month'} =~ m!^(\d{4})\-?(\d{2})$!;
		$opts{'one_month'} = "$1-$2";
	}

	print Dumper(%opts) if ( $opts{'debug'} >= 2); 

	#------------------------
	# Launch stats retrieving
	#------------------------

	print "@@@ Be aware that detailed data about DNS servers (asn, country) are not available before " . START_DATE . "! \n\n";
	$at = now();
	print "Starting data retrieving at $at ...\n" if ($opts{'debug'} >= 1);

	$dbh = DBI->connect($database, $user, $passwd) or die "cannot open $database $DBI::errstr \n";

	if ( $opts{'all_runs'} ) {
		GetStats();

	} elsif ( $opts{'one_run'} ) {
		GetStats('run', $opts{'one_run'});

	} elsif ( $opts{'one_month'} ) {
		GetStats('month', $opts{'one_month'});

	} else {
		# nope !
	}

	##---------------------------
	## Compute month averages
	##---------------------------

	&MonthAverages();  


	##---------------------------
	## Print results
	##---------------------------

	my $at = now();
	print "Printing results at $at ... \n" if ( $opts{'debug'} >= 2 );


	my $fh;
	if ( $opts{'output'} ) {
		$fh = fopen $opts{'output'}, 'w' or die "caanot open $opts{'output'} : $! \n";
	} else {
		$fh = \*STDOUT;
	}


	my ( @domains, $domain, $sdata, $strg, @data) ;

	my @months = sort { $a cmp $b } (keys %Stats);

	foreach my $month ( @months ) {

		print $fh "####--------------------------------------------------\n";
		print $fh "##    Mois : $month \n";
		print $fh "####--------------------------------------------------\n";


		@domains =  sort { $a cmp $b } (keys %{$Stats{$month}}) ;
		foreach $domain ( @domains ) {
			@data = @{$Stats{$month}{$domain}};
			$sdata = scalar ( @data );
			$strg = join ', ', @data[1..$#data];
			printf $fh "%40s - AS %d - $strg \n", $domain, $data[0];
		}

	}

	close $fh;

	$dbh->disconnect();
}


####------------------------
## usage($message)
####------------------------

sub usage {

	my $message = shift;

	print "\n Error: $message \n\n" if ($message);

	print "usage: $Name [--help|-h] [--debug|-d <debug-level>] [--all_runs|-a] [--one_month|-m <YYYY-MM>] [--one_run|-r <uuid or date>] \n";
	print "             [--output|-o <output-file>] \n";

}


####------------------------
## now()
####------------------------

sub now {

	my ($hour, $min, $sec) = (localtime(time))[2,1,0];
	return sprintf "%02d:%02d:%02d",$hour, $min, $sec;
}


####--------------------------------------------------
## &MonthAverages()
##
## Groups and computes statistics by month
####--------------------------------------------------

sub MonthAverages {


}


####---------------------------------------------------
## GetStats($type,$run)
##
## Get statistics.
## - If nothing is passed as parameter, it will
## fecth all statistics found in the database.
## - If $type eq 'month', $run will be interpreted as the
## month for which statistics will be retrieved.
## - If $type eq 'run', $run will be interpreted as either
## the run uuid or the run date and statistics will be 
## retreived for this run.
####---------------------------------------------------

sub GetStats {

	my $type   = shift;
	my $run    = shift; 

	my $at = now();
	print "GetStats at $at \n" if ($opts{'debug'} >= 2);

	my $href_runs;

	if ( $type eq 'month' ) {
		$href_runs = GetRuns($run);

	} elsif ( $type eq 'run' ) {
		$href_runs = GetOneRun($run);

	} elsif ( not defined $type ) {
		$href_runs = GetRuns();
	}

	my @res = ();

	foreach my $uuid (keys %{$href_runs} ) {
		GetStatsByRun($uuid, $href_runs->{$uuid}{'date'});
	}


}






####==============================================
####   Database sql instructions
####==============================================


####----------------------------------
##  $ref_uuids = GetRuns($month); 
##
## Get the uuid for all the runs of $month 
## sorted by date ascending.
## If month not specified, will return all uuid.
## Return a hash, where the keys are the uuid,
## and the secondary key is the date.
## access : $date = $ref_uuids{$uuid}{'date'}  
####----------------------------------

sub GetRuns {

	my $month = shift;

	my $filter = '';
	my $ref_runs = {};
	my @row;

	print "GetRuns --> argument : $month \n" if ( $opts{'debug'} >= 2 );

	if ( $month =~ m!^\d{4}\-\d{2}$! ) {

		$month = $month . '-01'; 
		$filter = qq{where date_trunc('month',date) = TIMESTAMP '$month'};
	} else {
		$filter = qq{where date_trunc('month',date) >= TIMESTAMP '} . START_DATE . q{'};
	}

	my $sql = q{select uuid, date from runs } . $filter . q{order by date}; 
	my $sth = $dbh->prepare($sql);
	$sth->execute();

	while ( @row = $sth->fetchrow_array() ) {
		$ref_runs->{$row[0]}{'date'} = $row[1];
		print "GetRuns --> $row[0] - $row[1] \n" if ( $opts{'debug'} >= 2 );
	}

	return $ref_runs;
}


####----------------------------------
##  $ref_uuid = GetOneRun($date); 
##
## Return a hash, where the key is the uuid,
## and the secondary key is the date corresponding
## of the uuid date in the 'runs' table.
## access : $date = $ref_uuids{$uuid}{'date'}  
####----------------------------------

sub GetOneRun {

	my $run = shift;

	my $filter = '';
	my $ref_runs = {};
	my @row;

	if ( $run =~ m!^\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}$! ) {
		$filter = qq{where date_trunc('minute',date) = TIMESTAMP'$run' };
	} else {
		$filter = qq{where uuid = '$run' };
	}

	my $sql = q{select uuid, date from runs } . $filter . q{order by date}; 
	my $sth = $dbh->prepare($sql);
	$sth->execute();

	while ( @row = $sth->fetchrow_array() ) {
		$ref_runs->{$row[0]}{'date'} = $row[1];
	}

	return $ref_runs;
}


####---------------------------------------------
##
##  &GetStatsByRun($uuid);
##
## Store data in %StatsByZone, %StatsByCountries 
## and %StatsByAs on a monthly basis.
####---------------------------------------------

sub GetStatsByRun {

	my $run = shift;
	my $date = shift;

	my ($month, @row, $current_broker, %current_zone);
	my ($nb_srv, $nb_as, $nb_cc);

	($month = $date) =~ s!^(\d{4}\-\d{2}).*$!$1!;

	my $at = now();
	print "GetStatsByRun for $run at $at \n" if ($opts{'debug'} >= 3);

	my $sql = qq{ select t.broker, t.asn, t.ip from tests_ns_zone t, broker b where b.uuid = '$run' and b.id = t.broker order by t.broker };
	my $sth = $dbh->prepare($sql);
	$sth->execute();
	
	print "1st sql statement \n" if ( $opts{'debug'} >=4 );

	my $sql2 = qq{select z.zone from zones z, broker b where b.zone=z.id and b.id = ?};
	my $sth2 = $dbh->prepare($sql2);
	print "2nd sql statement \n" if ( $opts{'debug'} >=4 );

	my $sql3 = qq{select address from ip where id = ?};
	my $sth3 = $dbh->prepare($sql3);
	print "3rd sql statement \n" if ( $opts{'debug'} >=4 );

	$current_broker = 0;
	my ($domain_name, $asn, @ips, $ip, $Nbs );

	while ( @row = $sth->fetchrow_array() ) {

		print "one row read \n" if ( $opts{'debug'} >=4 );

		if ( $current_broker != $row[0] ) {

			## store data for current broker 
		    ## Domain name, AS, DNS servers ip addresses 	

			if ( exists $current_zone{'broker'} ) {

				my $nbas = scalar ( keys %{$current_zone{'as'}} );
				print " broker $current_zone{'broker'} : $nbas AS \n" if ( $opts{'debug'} >=2 );
				if ( $nbas == 1 ) {

					 $asn = ( keys %{$current_zone{'as'}} )[0] ;

					$sth2->execute($current_broker); 
					( $domain_name ) = $sth2->fetchrow_array();

					@ips = ();
					foreach my $srv ( @{$current_zone{'servers'}} ) {
						$sth3->execute($srv);
						($ip) = $sth3->fetchrow_array();
						push (@ips, $ip);
					}
					$Stats{$month}{$domain_name} = [];
					$Stats{$month}{$domain_name}[0] =  $asn;
					for (my $i =1; $i <= scalar (@ips) ; $i++ ) {
						$Stats{$month}{$domain_name}[$i] = @ips[$i-1];
					}
					printf "added : $domain_name - $asn - %d servers \n", scalar (@ips) if ( $opts{'debug'} >=2 );
				}

				delete $current_zone{'broker'};
				delete $current_zone{'servers'};
				delete $current_zone{'as'};
				$Nbs = 0;

			}
			$current_broker = $row[0];	
		}

		$current_zone{'broker'} =  $row[0]; 
		$current_zone{'as'}{$row[1]} = 1;
		push @{$current_zone{'servers'}}, $row[2]; 
		$Nbs += 1;
		print "\t\tpushed $Nbs servers for current zone \n" if ( $opts{'debug'} >= 4 );


	}

}




