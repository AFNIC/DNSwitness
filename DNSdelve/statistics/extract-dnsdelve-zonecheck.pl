#!/usr/bin/perl

use strict;
use DBI;
use vars qw ( @ARGV );
use Getopt::Long;  
use File::Basename;
use File::Open qw(fopen);
use Data::Dumper;

our $Name = basename($0);

our $database = 'dbi:Pg:' . 'dbname=zonecheck';
our $user   = '';
our $passwd = '';
our $dbh;
our $at;

our %opts;
our %Stats;
our %MonthlyStats;
our %ErrorTypes;
use constant MAX_NB_FREQUENT_ERRORS => 5000;
use constant MAX_NB_PROVIDERS => 10;

MAIN: {

	#--------------------------
	# read command line options
	#---------------------------

	my $msg;


	GetOptions(\%opts, "help|h", "debug|d:i", "all_runs|a", "one_run|r:s", "one_month|m:s", "multiple_errors|e", "output|o:s", "full|f", "month_average|g");

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
		$opts{'one_month'} = "$0-$1";
	}

	print Dumper(%opts) if ( $opts{'debug'} >= 2); 

	#------------------------
	# Launch stats retrieving
	#------------------------

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

	&MonthAverages();  #Do it anyway. Needed for error types

	##---------------------------
	## Get stat. details (error types)
	##---------------------------

	if ( $opts{'full'} ) {
			
			$at = now();
			print "Getting error types at $at ...\n";
			GetErrorTypes();
		
	}
	


	##---------------------------
	## Print results
	##---------------------------

	my $fh;
	if ( $opts{'output'} ) {
		$fh = fopen $opts{'output'}, 'w' or die "caanot open $opts{'output'} : $! \n";
	} else {
		$fh = \*STDOUT;
	}

	print $fh "####---------------------------------------------------------------------------------\n";
	print $fh "#     Mois - Taux tests ZC positifs - Taux tests ZC negatifs - Nb domaines examines (Nb moyen de domaines examines par run)\n";
	print $fh "####----------------------------------------------------------------------------------\n\n";

	my ($ct, $cf, $cn, $ca);
	my ($date);

	if ( $opts{'month_average'} ) {

		my @months = sort { $a cmp $b } ( keys %MonthlyStats );
		foreach my $month ( @months ) {

			$ct = ( $MonthlyStats{$month}{'true'} / $MonthlyStats{$month}{'count'} ) * 100;
			$cf = ( $MonthlyStats{$month}{'false'} / $MonthlyStats{$month}{'count'} ) * 100;
			$cn = $MonthlyStats{$month}{'nb_domains'};
			$ca = $MonthlyStats{$month}{'nb_domains'} / $MonthlyStats{$month}{'count'} ;

			printf $fh "%-15s ---   %02.2f%s   ---   %02.2f%s    ---   %d (%d)\n", $month, $ct,'%', $cf, '%',$cn, $ca;
		}

	} else {

		my @uuids = sort { $Stats{$a}{'date'} cmp $Stats{$b}{'date'} } ( keys %Stats );
		foreach my $uuid ( @uuids ) {
		
			$Stats{$uuid}{'date'} =~ m!^(.*)\..*$! ;		
			$date =  $1 ;	
			$ct   = $Stats{$uuid}{'true'} * 100;
			$cf   = $Stats{$uuid}{'false'} * 100;
			$cn   = $Stats{$uuid}{'nb_domains'};
			printf $fh "%-15s ---   %02.2f%s   ---   %02.2f%s   ---   %d (-)\n", $date, $ct , '%', $cf, '%', $cn;
		}

	}

	##---------------------------
	## Print detailed results
	##---------------------------

	if ( $opts{'full'} ) {

		my @months = sort { $a cmp $b } ( keys %ErrorTypes );

		print $fh "\n\n####--------------------------------------------------\n";
		print $fh "#Erreurs les plus frequentes \n";
		print $fh "####--------------------------------------------------\n";
		foreach my $month ( @months ) {

			print $fh "\n#----------------------------\n";
			print $fh "# Mois : $month \n";
			print $fh "#----------------------------\n";

			my @frqs = sort { $ErrorTypes{$month}{'errors'}{$b} <=> $ErrorTypes{$month}{'errors'}{$a} } (keys $ErrorTypes{$month}{'errors'} );
			#$cf = $MonthlyStats{$month}{'nbt_errors'} ;
			$cf = $ErrorTypes{$month}{'nbt_errors'};

			for ( my $i =0; $i < scalar(@frqs) and $i < MAX_NB_FREQUENT_ERRORS - 1 ; $i++) {
				printf $fh "%-60s : %02.2f \n", $frqs[$i], ( $ErrorTypes{$month}{'errors'}{$frqs[$i]} / $cf ) * 100;
			}

		}

		print $fh "\n\n####--------------------------------------------------\n";
		print $fh "#Domaines de second niveau generant le plus d'erreurs \n";
		print $fh "####--------------------------------------------------\n";
		foreach my $month ( @months ) {

			print $fh "\n#----------------------------\n";
			print $fh "# Mois : $month \n";
			print $fh "#----------------------------\n";

			my @frqs = sort { $ErrorTypes{$month}{'providers'}{$b} <=> $ErrorTypes{$month}{'providers'}{$a} } (keys $ErrorTypes{$month}{'providers'} );
			$cf = $MonthlyStats{$month}{'raw_false'} ;

			for ( my $i =0; $i < scalar(@frqs) and $i < MAX_NB_PROVIDERS - 1 ; $i++) {
				printf $fh "%-25s : %02.2f \n", $frqs[$i], ( $ErrorTypes{$month}{'providers'}{$frqs[$i]} / $cf ) * 100;
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
	print "             [--multiple_errors|e] [--month_average|-g] [--full|-f] [--output|-o <output-file>] \n";

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

	my ($uuid, $month, $current_month );

	print "MonthAverages ... \n" if ( $opts{'debug'} >= 2 );

	my @uuids = keys ( %Stats );
	@uuids = sort { $Stats{$a}{'date'} cmp $Stats{$b}{'date'} } @uuids; # sort Stats by date

	$current_month = '1970-01';

	foreach $uuid ( @uuids ) {
		$month = $Stats{$uuid}{'date'};
		$month =~ s!^(\d{4}\-\d{2}).*$!$1!;

		unless ( $month eq $current_month ) {
			$current_month = $month;
			$MonthlyStats{$current_month}{'true'}   = 0;
			$MonthlyStats{$current_month}{'false'}  = 0;
			$MonthlyStats{$current_month}{'nb_domains'}  = 0;
			$MonthlyStats{$current_month}{'count'}       = 0;
		}
		$MonthlyStats{$current_month}{'true'}  += $Stats{$uuid}{'true'};     # proportion of domains with status ='t'!
		$MonthlyStats{$current_month}{'false'} += $Stats{$uuid}{'false'};	 # proportion of domains with status ='f' !
		$MonthlyStats{$current_month}{'raw_false'} += $Stats{$uuid}{'raw_false'};
		$MonthlyStats{$current_month}{'nb_domains'} += $Stats{$uuid}{'nb_domains'};
		$MonthlyStats{$current_month}{'count'} += 1;

		print "MonthAverages : $current_month - T : $MonthlyStats{$current_month}{'true'} - F : $MonthlyStats{$current_month}{'false'} \n" if ( $opts{'debug'} >= 3 );
	}
}


####---------------------------------------------------
## GetStats($type,$run)
##
## Get Zonecheck statistics.
## If nothing is passed as parameter, it will
## fecth all statistics found in the database.
## If $type eq 'month', $run will be interpreted as the
## for which statistics will be retrieved.
## If $type eq 'run', $run will be interpreted as either
## the run uuid or the run date and statistics will be 
## retreived for this run.
####---------------------------------------------------

sub GetStats {

	my $type   = shift;
	my $run    = shift; 

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
		@res = GetStatsByRun($uuid);
		$Stats{$uuid}{'date'}  = $href_runs->{$uuid}{'date'};
		$Stats{$uuid}{'true'}  = $res[0] / ( $res[0] + $res[1] );   # proportion of domains with status='t'
		$Stats{$uuid}{'false'} = $res[1] / ( $res[0] + $res[1] );   # proportion of domains with status='f' 
		$Stats{$uuid}{'raw_false'}  = $res[1] ;					    # total number of domains with status='f'
		$Stats{$uuid}{'nb_domains'} = $res[0] + $res[1] ;		    # total number of domains tested in the run
	}


}



####----------------------------------
#### &GetErrorTypes()
####
#### Scan %Stats and get most frequent 
#### type of errors. Results are stored
#### in %ErroTypes
####----------------------------------

sub GetErrorTypes {

	my @uuids = keys %Stats;
	foreach my $uuid ( @uuids ) {
		GetandTrimErrors($uuid);
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

	if ( $month =~ m!^\d{4}\-\d{2}$! ) {

		$month = $month . '-01'; 
		$filter = q{where date_trunc('month',date) = TMESTAMP'$month' };
	}

	my $sql = q{select uuid, date from runs } . $filter . q{order by date}; 
	my $sth = $dbh->prepare($sql);
	$sth->execute();

	while ( @row = $sth->fetchrow_array() ) {
		$ref_runs->{$row[0]}{'date'} = $row[1];
	}

	return $ref_runs;
}


####----------------------------------
##  $ref_uuid = GetOneRun($day); 
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
		$filter = qq{where date_trunc('minute',date) = TMESTAMP'$run' };
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
## my ($count_ok, $count_nok) = GetStatsByRun($uuid);
##
## Return the number of 'true' and 'false' 
## status for ZoneCheck tests for the run 
## corresponding to uuid
####---------------------------------------------

sub GetStatsByRun {

	my $run = shift;

	my $sqlt = qq{ select count(*) from tests where uuid='$run' and status = 't'};
	my $sqlf = qq{ select count(*) from tests where uuid='$run' and status = 'f'};

	my $stht = $dbh->prepare($sqlt);
	my $sthf = $dbh->prepare($sqlf);
	$stht->execute();
	$sthf->execute();

	my ($ct) = $stht->fetchrow_array();
	my ($cf) = $sthf->fetchrow_array();

	return ($ct, $cf);
}


####---------------------------------------------
#### &GetandTrimErrors($uuid)
####
#### Get most frequent errors for run $uuid
#### group results by month into %ErrorTypes
####---------------------------------------------

sub GetandTrimErrors {

	my $uuid = shift;

	my $month = $Stats{$uuid}{'date'};
	$month =~ s!^(\d{4}\-\d{2}).*$!$1!;

	my ($domain, $message, @types, @providers, $type, $provider);

	my $sql = qq{ select domain, message from tests where status='f' and uuid='$uuid' };
	my $sth = $dbh->prepare($sql);
	$sth->execute;

	while ( ($domain, $message) = $sth->fetchrow_array() ) {

		@types     = ();
		@providers = ();

		if ( $opts{'multiple_errors'} ) {
			GetErrorTypeMul($domain, $message, \@types, \@providers);
		} else {
			GetErrorType($domain, $message, \@types, \@providers);
		}

		printf "$uuid - Nb errors = %d - Nb providers = %d \n", scalar(@types), scalar(@providers) if ($opts{'debug'} >= 3);

		foreach $type ( @types ) {	
			$ErrorTypes{$month}{'errors'}{$type}        += 1;		# The same error type can be counted multiple times by domain
			$ErrorTypes{$month}{'nbt_errors'}           += 1;		# Total number of errors for one month 
			printf "$uuid - %-40s - %s \n", $domain, $type if ($opts{'debug'} >= 3);
		}
		foreach $provider ( @providers ) {	
			$ErrorTypes{$month}{'providers'}{$provider} += 1;      # A particular provider is counted only once by domain
			printf "$uuid - %-40s - %-15s \n", $domain, $provider if ($opts{'debug'} >= 3);
		}
	
	}
	

}

####---------------------------------------------
#### GetErrorType($message, $domain, $ref_type, $ref_provider)
####
#### Parse $message and find error type and DNS provider
#### that caused Zonecheck error
#### 
#### Results are stored into the 2 ref. to arrays 
#### $ref_type and $ref_provider
####---------------------------------------------
sub GetErrorType {

	my $domain       = shift;
	my $message      = shift;
	my $ref_type     = shift;
	my $ref_provider = shift;

	my $type     = 'undefined';
	my $provider = 'undefined';

	my @lines;

	#if ( $message =~ m!\s+fatal\s+.*f>!m ) {
	if ( $message =~ m!\bfatal\b!m ) {

		$message =~ s!^.*f\>!!s;         # remove every thing before 'f>'
		@lines = split /\n/, $message;
		$type = $lines[0];              # error type in is in the 1st line 
		$type =~ s!^.*\[(.*)\].*$!$1!;  # if there are [ ], only take what is in between
		$type =~ s!^\s+!!; $type =~ s!\s+$!!;

		for (my $i=1; $i < scalar(@lines); $i++) {
			if ( $lines[$i] =~ m!=>\s+(\S+)! ) {   # find a line starting with '=>'
				$provider = $1;
				$provider =~ s!^(.*)\/.*$!$1!;     # remove what is after '/'
				$provider =~ s!^[^\.]*\.!!;        # remove first label
				last;
			}
		}
	## Special cases
	} elsif ( $message =~ m!ERROR: The domain.*has\s+not\s+been\s+found\s+through\s+the\s+local\s+resolver!s ) {

		$type = 'domain not found through local resolver';

	} elsif ( $message =~ m!ERROR: Send failed to.*use_tcp=false, exception : stream closed!s ) {
		$type = 'socket error (dnswitness)';

	} elsif ( $message =~ m!ERROR: Unable to find a SOA record for that domain!s ) {
		$type = 'No SOA record for this domain';

	} elsif ( $message =~ m!Unable to identify primary nameserver!s ) {
		$type = 'Unable to identify primary nameserver (NS vs SOA)';

	} elsif ( $message =~ m!Unable to find nameserver IP address!s ) {
		$type = 'Unable to find nameserver IP addresses';

	} elsif ( $message =~ m!timelimit: sending kill signal 9!s ) {
		$type = 'socket time-out (dnswitness)';

	} else {
		$type = $message;
	}

	#return ($type, $provider);
	$ref_type->[0]     = $type;
	$ref_provider->[0] = $provider;
}



####---------------------------------------------
#### ($type, $provider) = GetErrorTypeMul($message, $domain)
####
#### Parse $message and find multiple error types and DNS provider
#### that caused Zonecheck error
#### 
#### Results are stored into the 2 ref. to arrays 
#### $ref_type and $ref_provider
####
#### Notice : a provider will be counted 1 for each 
#### erronuous domain. Hence, if a provider has 2 erronous
#### domains with 1 error each, it will appear as making 
#### more errors than a provider that will have 10 errors 
#### on only one domain.
####---------------------------------------------
sub GetErrorTypeMul {

	my $domain = shift;
	my $message = shift;
	my $ref_type     = shift;
	my $ref_provider = shift;

	my $type     = 'undefined';
	my $provider = 'undefined';
	my %seen     = {};

	## Lines like 'ns2.lwsdns.com/193.37.145.22' give $provider
	## Lines like 'ns2.lwsdns.com'               give $provider
	## my $dns_line_fmt = '([a-zA-z0-9\-]\.)*[a-zA-z0-9\-]\/([0-9]*[\.:])*[0-9]';
	my $dns_line_fmt = '^=> (([a-zA-z0-9\-]*\.)*)([a-zA-z0-9\-]*)(\/(([0-9A-F]*[\.:])*)([0-9A-F]*))?\s*$';

	my @lines;

	@lines = split /\n/, $message;

	print "======================================\n" if ($opts{'debug'} >= 4);
	print "FilterError - D50 - $domain \n" if ($opts{'debug'} >= 4);

	for (my $i=1; $i < scalar(@lines); $i++) {

		unless ( ($lines[$i] =~ m!^f> !) or ($lines[$i] =~ m!^=> !)) {
			next;
		}

		print "FilterError - D52 - $lines[$i] \n" if ($opts{'debug'} >= 4);

		## Lines like 'ns2.lwsdns.com/193.37.145.22' give $provider
		if ( $lines[$i] =~ m!$dns_line_fmt! ) {
			$provider = $lines[$i];
			$provider =~ s!^=>(.*)$!$1!;     # remove leading '=>'
			$provider =~ s!^(.*)\/.*$!$1!;   # remove IP address
			$provider =~ s!^[^\.]*\.!!;      # remove first label
			unless ( $seen{$provider} or ($provider =~ m!^\s*generic\s*$! )) {   #Count a provider only once by domain ! 
				$seen{$provider} = 1;
				push (@$ref_provider, $provider);
				printf "FilterErrorP :  %-40s - %-15s \n", $domain, $provider if ($opts{'debug'} >= 4);
			}
			
		} else {
			$type = $lines[$i];
			$type =~ s!^f>(.*)$!$1!;      			# remove leading 'f>'
			$type =~ s!^=>(.*)$!$1!;      			# remove leading '=>'
			$type =~ s!^\s*!!; $type =~ s!\s*$!!;  	#remove leading/trailing blanks
			unless ( $type =~ m!^\[.*\]! ) {	 	# errors like '[....]' are tests that couldn't be completed for some reason
				push(@$ref_type, $type);
			}
			printf "FilterErrorT :  %-40s - $type\n", $domain if ($opts{'debug'} >= 4);
		}

	}



}
