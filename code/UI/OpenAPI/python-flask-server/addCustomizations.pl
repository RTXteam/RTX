#!/usr/bin/perl
#
################################################################################
# Program     : addCustomizations.pl
# Author      : Eric Deutsch <edeutsch@systemsbiology.org>
# Date        : 2018-03-09
#
# Description : This program adds the minimal custom changes to the swagger
#               autogen code
#
#  % addCustomizations.pl
#
###############################################################################

  use strict;
  use warnings;

  main();
  exit(0);


###############################################################################
sub main {

  my $filename = "query_controller.py";
  unless ( -e $filename ) {
    print "ERROR: Must be run in the controllers/ directory with file $filename present\n";
    return;
  }

  #### Get the properties of the original file and open it
  my @properties = stat($filename);
  my $mode = $properties[2];
  open (INFILE,$filename) || die "Unable to open $filename for read";

  #### Open a change file for output
  open (OUTFILE,"> $filename.replaceall") || die "Unable to open $filename.replaceall for write";

  #### Begin with a cleared changed flag
  my $status=0;
  print "INFO: Injecting customization code in $filename\n";

  #### Read through the file line by line, making changes as appropriate
  while (my $line = <INFILE>) {
    if ( $status == 0 ) {
      print OUTFILE $line;
      if ( $line =~ /from swagger_server import util/ ) {
	print OUTFILE "from RTXQuery import RTXQuery\n";
        $status = 1;
        next;
      }
    }

    if ( $status == 1 ) {
      print OUTFILE $line;
      if ( $line =~ /if connexion.request.is_json:/ ) {
	print OUTFILE "        query = connexion.request.get_json()\n";
	print OUTFILE "        rtxq = RTXQuery()\n";
	print OUTFILE "        result = rtxq.query(query)\n";
	print OUTFILE "    return result\n";
        $status = 2;
	last;
      }
    }
  }

  close(INFILE);
  close(OUTFILE);

  if ( $status != 2 ) {
    print "ERROR parsing $filename. status = $status\n";
    return;
  }

  rename("$filename.replaceall",$filename);
  chmod($mode,$filename);

  
  $filename = "translate_controller.py";
  unless ( -e $filename ) {
    print "ERROR: Must be run in the controllers/ directory with file $filename present\n";
    return;
  }

  #### Get the properties of the original file and open it
  @properties = stat($filename);
  $mode = $properties[2];
  open (INFILE,$filename) || die "Unable to open $filename for read";

  #### Open a change file for output
  open (OUTFILE,"> $filename.replaceall") || die "Unable to open $filename.replaceall for write";

  #### Begin with a cleared changed flag
  $status=0;
  print "INFO: Injecting customization code in $filename\n";

  #### Read through the file line by line, making changes as appropriate
  while (my $line = <INFILE>) {
    if ( $status == 0 ) {
      print OUTFILE $line;
      if ( $line =~ /from swagger_server import util/ ) {
	print OUTFILE "import os\n";
	print OUTFILE "import sys\n";
	print OUTFILE "sys.path.append(os.path.dirname(os.path.abspath(__file__))+\"/../../../../../reasoningtool/QuestionAnswering/\")\n";
	print OUTFILE "from QuestionTranslator import QuestionTranslator\n";
        $status = 1;
        next;
      }
    }

    if ( $status == 1 ) {
      print OUTFILE $line;
      if ( $line =~ /if connexion.request.is_json:/ ) {
	print OUTFILE "        question = connexion.request.get_json()\n";
	print OUTFILE "        txltr = QuestionTranslator()\n";
	print OUTFILE "        query = txltr.translate(question)\n";
	print OUTFILE "    return query\n";
        $status = 2;
	last;
      }
    }
  }

  close(INFILE);
  close(OUTFILE);

  if ( $status != 2 ) {
    print "ERROR parsing $filename. status = $status\n";
    return;
  }

  rename("$filename.replaceall",$filename);
  chmod($mode,$filename);

}

