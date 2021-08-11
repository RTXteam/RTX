#!/usr/bin/perl

use strict;
use warnings;

use HTTP::Request;
use LWP::UserAgent;
use JSON::Parse;

my $url = 'https://arax.ncats.io/api/arax/v1.1/query';
my $json = '{ "message": { "query_graph":
{
   "edges": {
      "e00": {
         "subject":   "n00",
         "object":    "n01",
         "predicates": ["biolink:physically_interacts_with"]
      }
   },
   "nodes": {
      "n00": {
         "ids":        ["CHEMBL.COMPOUND:CHEMBL112"]
      },
      "n01": {
         "categories":  ["biolink:Protein"]
      }
   }
}

} }
';

my $request = HTTP::Request->new( 'POST', $url );
$request->header( 'Content-Type' => 'application/json' );
$request->content( $json );

my $lwp = LWP::UserAgent->new;
my $lwp_response = $lwp->request( $request );

my @results_list = ();
my $counter = 1;

if ( $lwp_response->is_success() ) {
  my $response = JSON::Parse::parse_json($lwp_response->content());
  if ( $response->{'message'} && $response->{'message'}->{'results'} ) {
    my @result_list = @{$response->{'message'}->{'results'}};
    foreach my $result (@result_list) {
      my $essence = $result->{'essence'};
      push(@results_list,[ $counter, $essence ]);
      $counter++;
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


