#!/usr/bin/perl

use strict;
use warnings;

use HTTP::Request;
use LWP::UserAgent;
use JSON::Parse;

my $url = 'http://rtx.ncats.io/devED/api/rtx/v1/query';
my $json = '{"query_type_id": "Q3", "terms": { "chemical_substance": "CHEMBL:CHEMBL521" } }';
my $request = HTTP::Request->new( 'POST', $url );
$request->header( 'Content-Type' => 'application/json' );
$request->content( $json );

my $lwp = LWP::UserAgent->new;
my $lwp_response = $lwp->request( $request );

my @results_list = ();

if ( $lwp_response->is_success() ) {
  my $response = JSON::Parse::parse_json($lwp_response->content());
  if ( $response->{'result_list'} ) {
    my @result_list = @{$response->{'result_list'}};
    foreach my $result (@result_list) {
      my $text_result = $result->{'text'};
      if ( $result->{result_graph} ) {
        foreach my $node ( @{$result->{result_graph}->{node_list}} ) {
          if ( $node->{type} eq 'protein' ) {
            push( @results_list, [ $node->{id}, $node->{name} ] );
          }
        }
      }
    }
  } else {
    print($response->{message}."\n")
  }

} else {
    print("ERROR: " . $lwp_response->status_line());
}

foreach my $result ( @results_list ) {
  print join("\t",@{$result})."\n";
}


