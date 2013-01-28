#!/usr/bin/perl

use strict;
use DBI;
use vars qw ( @ARGV );
use Getopt::Long;  
use File::Basename;
use File::Open qw(fopen);
use Data::Dumper;

our $Name = 'split-zonefile';

our $at;
our %opts;
our $input;
our $inout_dir;
our $TotalZones = 0;
our $TotalFiles = 0;


MAIN: {

	#--------------------------------------
	# read command line options & arguments
	#-------------------------------------

	my $msg;

	GetOptions(\%opts, "help|h", "debug|d:i", "zones_number|n:i", "prefix|p:s", "suffix_length|s:i");

	if ( $opts{'help'} ) {
		usage();
		exit(0);
	}

	if ( scalar(@ARGV) != 1 ) {
		$msg = qq{the zonefile to be splitted must be provided as the unique argument};
		usage($msg);
		exit(1);
	}
	$input     = basename($ARGV[0]);
	$inout_dir = dirname($ARGV[0]);

	#------------------
	# Default options
	#------------------
	unless (exists $opts{'debug'}) {
		$opts{'debug'}   = 1;
	}

	unless (exists $opts{'zones_number'}) {
		$opts{'zones_number'} = 250000;  		# 250.000 = 10% of 2.500.000
	}

	unless (exists $opts{'suffix_length'}) {
		$opts{'suffix_length'} = 2;
	}

	unless (exists $opts{'prefix'}) {
		$opts{'prefix'} = $input;
	}


	print Dumper(%opts) if ( $opts{'debug'} >= 2); 

	#------------------------
	# Launch zonefile splitting
	#------------------------

	SplitIt();

	print "$TotalFiles files written. $TotalZones zones found. \n";
}


####------------------------
## usage($message)
####------------------------

sub usage {

	my $message = shift;

	print "\n Error: $message \n\n" if ($message);

	GetOptions(\%opts, "help|h", "debug|d:i", "zones_number|n:i", "prefix|p:s", "suffix_length|s:i");

	print "usage: $Name [Options] zonefile \n";
	print "\n";
	print "zonefile : file to be splitted \n";
	print "Options  : \n";
	print "  --debug|-d <debug-level>    : debug level (default : 1) \n";
	print "  --zones_number|-n <number>  : number of zones in each output file (default : 250.000) \n";
	print "  --prefix|-p <PREFIX>        : output filenames prefix (default : input filename) \n";
	print "  --suffix_length|-s <number> : suffix length for output files. Output filenames are in the form PREFIXaa, PREFIXab ... (default : 2) \n";

}


####------------------------
## now()
####------------------------

sub now {

	my ($hour, $min, $sec) = (localtime(time))[2,1,0];
	return sprintf "%02d:%02d:%02d",$hour, $min, $sec;
}


####------------------------
## SplitIt()
####------------------------

sub SplitIt {

#####  GetOptions(\%opts, "help|h", "debug|d:i", "zones_number|n:i", "prefix|p:s", "suffix_length|s:i");

	my $infile = $inout_dir . '/' . $input;	
	my $ifh    = fopen $infile, 'r';

	my $outfile_fmt  = $inout_dir . '/' . $opts{'prefix'} ;
	my $suffix       = GetNextSuffix();
	my $outfile      = $outfile_fmt . $suffix ;
	my $ofh          = fopen $outfile, 'w';
	$TotalFiles      = 1;
	my $nb_zones = 0;
	my $current_zone = '';
	my $zone;
	my $line;

	while ( $line = <$ifh> ) {

		next if ( $line =~ m!^;! );  # skip comments
		($zone = $line) =~ s!^(\S+)\.\s+.*$!$1\.! ;

		if ( $zone ne $current_zone ) {

			if ($nb_zones == $opts{'zones_number'}) {

				close $ofh;
				print "wrote $nb_zones zones in $outfile \n" if ( $opts{'debug'} >= 1 );
				$suffix   = GetNextSuffix($suffix);
				$outfile  = $outfile_fmt . $suffix ;
				$ofh      = fopen $outfile, 'w'; 
				$TotalFiles++;
				$nb_zones = 0;

			}

			$nb_zones += 1;
			$TotalZones++;
			$current_zone = $zone;

		}

		print $ofh $line;
	}

	print "wrote $nb_zones zones in $outfile \n" if ( $opts{'debug'} >= 1 );
	close $ofh;
	close $ifh;
}


####---------------------------------
## GetNextSuffix($current_suffix)
##
## If $current_suffix is given,
## it will return, next suffix.
## Otherwise, will return 1st suffix.
####--------------------------------

sub GetNextSuffix {

	my $current_suffix = shift;

	my $n = $opts{'suffix_length'};

	if ( $current_suffix ) {
		$current_suffix++;
	} else {
		for (my $i=0; $i < $n ; $i++) {
			$current_suffix .= 'a';
		}
	}
	return $current_suffix;
}


