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
our %StatsByZones;
our %StatsByCountries;
our %StatsByAs;
our %MonthlyStats;

use constant START_DATE => '2011-08-01';  #Details about DNS servers were not stored in db, before this date.
use constant TOP => 5;

MAIN: {

	#--------------------------
	# read command line options
	#---------------------------

	my $msg;


	GetOptions(\%opts, "help|h", "debug|d:i", "all_runs|a", "one_run|r:s", "one_month|m:s", "output|o:s", "full|f");

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
	unless ( exists $opts{'full'} ) {
		$opts{'full'} = 0;
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

	my (@nbrs, $j);

	my @months = sort { $a cmp $b } (keys %StatsByZones);

	foreach my $month ( @months ) {

		print $fh "####--------------------------------------------------\n";
		print $fh "##    Mois : $month \n";
		print $fh "####--------------------------------------------------\n";
		print $fh "Nombre de zones examinees : $MonthlyStats{$month}{'nb_zones'} \n";
		printf $fh "Nombre de serveurs / zone : moyenne = %9.3f , min = %d , max = %d \n", 
	                 $MonthlyStats{$month}{'srv'}{'avg'}, $MonthlyStats{$month}{'srv'}{'min'}, $MonthlyStats{$month}{'srv'}{'max'};
		
		printf $fh "Nombre de pays / zone     : moyenne = %9.3f , min = %d , max = %d \n", 
	                 $MonthlyStats{$month}{'cc'}{'avg'} , $MonthlyStats{$month}{'cc'}{'min'}, $MonthlyStats{$month}{'cc'}{'max'};

		printf $fh "Nombre de AS / zone       : moyenne = %9.3f , min = %d , max = %d \n", 
	                 $MonthlyStats{$month}{'as'}{'avg'}, $MonthlyStats{$month}{'as'}{'min'}, $MonthlyStats{$month}{'as'}{'max'};

		print $fh "\nTop ". TOP . " des pays :\n";
		print $fh "****************** \n";
		@nbrs = sort {$StatsByCountries{$month}{$b} <=> $StatsByCountries{$month}{$a} } (keys %{$StatsByCountries{$month}});
		$j = 0;
		for my $i ( @nbrs ) {
			printf $fh "$i : %15d - %2.3f \n", $StatsByCountries{$month}{$i}, $StatsByCountries{$month}{$i} / $MonthlyStats{$month}{'nb_servers'} ;
			$j += 1;
			last if ( $j == TOP );
		}

		print $fh "\nTop " . TOP . " des AS :\n";
		print $fh "****************** \n";
		@nbrs = sort {$StatsByAs{$month}{$b} <=> $StatsByAs{$month}{$a} } (keys %{$StatsByAs{$month}});
		$j = 0;
		for my $i ( @nbrs ) {
			printf $fh "AS %6d : %15d - %2.3f \n", $i, $StatsByAs{$month}{$i}, $StatsByAs{$month}{$i} / $MonthlyStats{$month}{'nb_servers'} ;
			$j += 1;
			last if ( $j == TOP );
		}

		if ( $opts{'full'} ) { 

			print $fh "\n";
			print $fh "##-------------\n";
			print $fh "##  Détails \n";
			print $fh "##-------------\n";

			print $fh "Serveurs par zone : \n";
			print $fh "****************** \n";
			@nbrs = sort { $a <=> $b } ( keys %{$StatsByZones{$month}{'srv'}} );
			for my $i ( @nbrs ) {
				printf $fh "$i serveurs : %15d - %2.3f \n", $StatsByZones{$month}{'srv'}{$i} , $StatsByZones{$month}{'srv'}{$i} / $MonthlyStats{$month}{'nb_zones'};
			}

			print $fh "Pays par zone : \n";
			print $fh "****************** \n";
			@nbrs = sort { $a <=> $b } ( keys %{$StatsByZones{$month}{'cc'}} );
			for my $i ( @nbrs ) {
				printf $fh "$i pays : %15d - %2.3f \n", $StatsByZones{$month}{'cc'}{$i} , $StatsByZones{$month}{'cc'}{$i} / $MonthlyStats{$month}{'nb_zones'};
			}

			print $fh "AS par zone : \n";
			print $fh "****************** \n";
			@nbrs = sort { $a <=> $b } ( keys %{$StatsByZones{$month}{'as'}} );
			for my $i ( @nbrs ) {
				printf $fh "$i AS : %15d - %2.3f \n", $StatsByZones{$month}{'as'}{$i} , $StatsByZones{$month}{'as'}{$i} / $MonthlyStats{$month}{'nb_zones'};
			}
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
	print "             [--full|-f] [--output|-o <output-file>] \n";

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
## Parse %Stats and store results in %MonthlyStats
####--------------------------------------------------

sub MonthAverages {

	my $at = now();
	print "MonthAverages at $at ... \n" if ( $opts{'debug'} >= 2 );

	my ($nb, $max, $min, $nb_zones);

	my @months = sort { $a cmp $b } ( keys %StatsByZones );

	foreach my $month ( @months ) {

		$nb_zones = 0;

		##------------------
		## average nb of servers 
		##------------------

		$nb= 0; $max = 0; $min = 500;
		foreach my $i (keys %{$StatsByZones{$month}{'srv'}} ) {
			$nb += $i * $StatsByZones{$month}{'srv'}{$i};
			$nb_zones += $StatsByZones{$month}{'srv'}{$i};
			$min = $i if ( $i < $min );
			$max = $i if ( $i > $max );
		}
		$MonthlyStats{$month}{'nb_zones'} = $nb_zones ;

		$MonthlyStats{$month}{'srv'}{'avg'} = $nb  / $nb_zones ;
		$MonthlyStats{$month}{'srv'}{'min'} = $min;
		$MonthlyStats{$month}{'srv'}{'max'} = $max;

		##------------------
		## average nb of countries
		##------------------

		$nb= 0; $max = 0; $min = 500;
		foreach my $i (keys %{$StatsByZones{$month}{'cc'}} ) {
			$nb += $i * $StatsByZones{$month}{'cc'}{$i};
			$min = $i if ( $i < $min );
			$max = $i if ( $i > $max );
		}
		$MonthlyStats{$month}{'cc'}{'avg'} = $nb  / $nb_zones ;
		$MonthlyStats{$month}{'cc'}{'min'} = $min;
		$MonthlyStats{$month}{'cc'}{'max'} = $max;
	
		##------------------
		## average nb of as
		##------------------

		$nb= 0; $max = 0; $min = 500;
		foreach my $i (keys %{$StatsByZones{$month}{'as'}} ) {
			$nb += $i * $StatsByZones{$month}{'as'}{$i};
			$min = $i if ( $i < $min );
			$max = $i if ( $i > $max );
		}
		$MonthlyStats{$month}{'as'}{'avg'} = $nb  / $nb_zones ;
		$MonthlyStats{$month}{'as'}{'min'} = $min;
		$MonthlyStats{$month}{'as'}{'max'} = $max;
	}
}


####---------------------------------------------------
## GetStats($type,$run)
##
## Get topology statistics.
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

	my $sql = qq{ select t.broker, t.ip, t.cc, t.asn from tests_ns_zone t, broker b where b.uuid = '$run' and b.id = t.broker order by t.broker };

	my $sth = $dbh->prepare($sql);
	$sth->execute();

	$current_broker = 0;

	while ( @row = $sth->fetchrow_array() ) {

		if ( $current_broker != $row[0] ) {

			## store data for this broker 
			if ( exists $current_zone{'servers'} ) {

				$nb_srv = $current_zone{'servers'};
				$nb_cc  = scalar ( keys %{$current_zone{'countries'}} );
				$nb_as  = scalar (keys %{$current_zone{'as'}} );

				$StatsByZones{$month}{'srv'}{$nb_srv} += 1;
				$StatsByZones{$month}{'cc'}{$nb_cc}   += 1;
				$StatsByZones{$month}{'as'}{$nb_as}   += 1;

				delete $current_zone{'servers'};
				delete $current_zone{'as'};
				delete $current_zone{'countries'};

			}
			$current_broker = $row[0];	
		}

		$current_zone{'servers'} += 1;
		$current_zone{'countries'}{$row[2]} = 1;
		$current_zone{'as'}{$row[3]} = 1;

		$StatsByCountries{$month}{$row[2]} += 1;
		$StatsByAs{$month}{$row[3]}        += 1;

		$MonthlyStats{$month}{'nb_servers'} += 1;


	}

}




