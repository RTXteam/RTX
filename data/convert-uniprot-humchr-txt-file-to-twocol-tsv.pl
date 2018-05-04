#!/usr/bin/perl -w

# To be blamed for this hack:  Stephen Ramsey

# usage:
#  mv uniprot.txt uniprot.txt.old
#  for name in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 x y
#  do
#    wget http://uniprot.org/docs/humchr${name}.txt
#    cat humchr${name}.txt | perl convert-uniprot-humchr-txt-file-to-twocol-tsv.pl >> uniprot.txt
#  done

my $header = 1;
while(defined(my $line = <STDIN>)) {
    chomp($line);
    if ($header == 1 && $line =~ /^Gene/) {
        <STDIN>;
        <STDIN>;
        $header = 0;
    }

    if ($header == 0 && $line !~ /^Gene/) {
        $line =~ s/\s+/\t/g;
        my @fields = split(/\t/, $line);
        my $gene_symbol = $fields[0];
        if ($gene_symbol eq "-") {
            last;
        }
        if ($gene_symbol =~ /^([^\-]+\-\D+\d)([\dxy]+q\d+\.\d)$/) {
            $gene_symbol = $1;
            $uniprot_id = $fields[1];
        }
        else {
            if ($gene_symbol =~ /^([^\-]+\-c\dorf\d+)([\dxy]+q\d+\.\d)$/) {
                $gene_symbol = $1;
                $uniprot_id = $fields[1];
            }
            else {
                $uniprot_id = $fields[2];
            }
        }
        print $uniprot_id . "\t" . $gene_symbol . "\n";
    }
}
