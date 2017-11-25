# NCATS Reasoning Tool Proof-of-Concept Planning Page
## Deadline: Nov. 29, 2017 (09:00 PST)

### last updated:  2017.11.24


- (BT1) Check into GitHub a script that solves Q1 to the best of our ability
  (i.e., for each of the 21 diseases, produce a ranked list of GCs with
  associated subgraphs; for the purpose of (1), this could be a JSON dump of the
  subgraph).  Bonus points if the script is commented.

- (BT2) Check into GitHub a script that solves Q2 to the best of our ability
  (i.e., for each of the 1,000 drug/disease pairs, produce a subgraph (again,
  keeping (2) self-contained, this could be JSON) spanning the drug, disease, a
  pathway, and an anatomy.  Bonus points if the script is commented.

    - Things that will help with BT2:
      - Steve to check into GitHub an extension of the q2 starting TSV file that has HP or DOID identifiers in Col3
      - push the updated KG to Lysine as soon as the code is confirmed to be working
      - get the UI up and running on Lysine
      
- (BT3) Make a slide deck (approx. 10 slides) that will guide our presentation
  and serve as insurance against unexpected demo failure. NOTE: the slide deck
  is actually due on Monday. Slides should be as follows:
	- (S1) our team (list people, expertise, and roles)
	- accomplishments so far:
		- (S2) Orangeboard
		- (S3) BioNetExpander
		- (S4) the KG that we have built 
		- (S5) MC subgraph finding
		- (S6) RWR maybe
		- (S7) screencap of our OpenAPI (for the parts we are able to connect to
          server-side functions by Wednesday)
		- (S8) screencap of UI mockup
	- our plan going forward:
		- (S9) show the architecture diagram from the proposal
		- (S10) show conceptual diagram of our markov chain approach
	- (S11) summary slide for our milestones

- (BT4) Somehow connect BT1 or BT2 (not sure we need both, as one of them will
  illustrate the point) to the UI mockup

**NOTE**: all four of the above items depend on having a relatively complete
KG to work with.  Thus we have one final BT item:

- (BT5) Complete knowledge graph so that it has the 21 Q1 diseases, the 8,000 Q1
  GCs, the 1,000 Q2 drugs and 1,000 Q2 diseases

Additional nice-to-haves:

- (NTH1) Working OpenAPI connected to script BT1, script BT2, or both
- (NTH2) Movie showing a dry-run of the demo, on screen sharing
