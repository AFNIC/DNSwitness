#!/usr/bin/perl

use DBI;


my $database = 'dbi:Pg:dbname=' . 'dnsdelve-ip';
my $user     = 'dnsdelve';

my %Stats = ();

my $dbh = DBI->connect($database, $user, $passwd) or die "cannot open $database $DBI::errstr \n";

my @Sql = (
	'select uuid, id, zone from v6_full' ,
	'select uuid, id, zone from v6_enabled',
	'select uuid, id, zone from v6_dns', 
	'select uuid, id, zone from v6_email',
	'select uuid, id, zone from v6_web',
);

for (my $i=0; $i <= 4; $i++ ) {

	GetDatafromView($i);

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
	my $file  = time() . '-' . $table . '.txt' ;

	$Stats[$table] = {};

	open(FILE, ">$file");
	my $sth = $dbh->prepare($sql);
	$sth->execute();

	while ( @row = $sth->fetchrow_array() ) {

		$string = join ('; ', @row);
		print FILE "$string \n";

		$Stats{$table}{$row[0]} += 1;    # stats by type and by uuid
	}

	close FILE;

}


################################
## PrintGlobalStats
################################

sub PrintGlobalStats {


	my $file = time() . '-' . 'global_stats.txt';

	my ($t_year, $t_month, $t_day, $t_hour, $t_min) = (localtime(time))[5,4,3,2,1];
	$t_year += 1900;
	$t_month += 1;
	$t_month = sprintf '%2d', $t_month;
	$t_day   = sprintf '%2d', $t_day;
	$t_hour  = sprintf '%2d', $t_hour;
	$t_min   = sprintf '%2d', $t_min;

	my $mfile = 'stats-dnsdelve-ipv6-' . $t_year . $t_month . $t_day . '-' . $t_hour . $t_min . '.txt';

	open(FILE, ">$file");
	open(MFILE, ">$mfile");

	my %StatByMonth = ();
	my ($k, $u, $n, $f, $p, $month, $date, $s );

	my $sql = "select date, numberdomains, samplingrate from runs where uuid=?";
	my $sth = $dbh->prepare($sql);

	foreach $k (keys %Stats ) {

		print FILE "####################\n";
		print FILE "#  Table $k \n";
		print FILE "####################\n";

		$StatByMonth{$k} = {};

		my @Uuid = sort { $a <=> $b } ( keys %{$Stats{$k}} );  # sort by uuid ascending

		## Get corresponding run date 

		foreach $u ( @Uuid ) {
			$sth->execute($u);
			($date, $n, $s ) = $sth->fetchrow_array();

			$f =  $Stats{$k}{$u} / $n * 100 ;
			$p = sprintf "%3.2f", $f ;
			print FILE "$date - $n - $Stats{$k}{$u} ($p) \n";

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
		print MFILE "#    (*) domaines repondant au critÃere de selection Ipv6 \nÄ\n";

		foreach $month ( @Months ) {
			
			printf MFILE "%s ; %3.2f ; %d \n", $month, $StatByMonth{$k}{$month}{'avg'} / $StatByMonth{$k}{$month}{'runs'} , $StatByMonth{$k}{$month}{'zone'} / $StatByMonth{$k}{$month}{'runs'};
			
		}
		

	}

	close FILE;
	close MFILE;
}
