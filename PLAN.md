# NCATS Reasoning Tool Proof-of-Concept Planning Page
## Deadline: Nov. 29, 2017 (09:00 PST)

### last updated:  2017.11.24


- (BT1) Check into GitHub a script that solves Q1 to the best of our ability (i.e., for each of the 21 diseases, produce a ranked list of GCs with associated subgraphs; for the purpose of (1), this could be a JSON dump of the subgraph).  Bonus points if the script is commented.

- (BT2) Check into GitHub a script that solves Q2 to the best of our ability (i.e., for each of the 1,000 drug/disease pairs, produce a subgraph (again, keeping (2) self-contained, this could be JSON) spanning the drug, disease, a pathway, and an anatomy.  Bonus points if the script is commented.

- (BT3) Make a slide deck (approx. 10 slides) that will guide our presentation and serve as insurance against unexpected demo failure:
	- (1) our team (list people, expertise, and roles)
	- accomplishments so far:
		- (2) Orangeboard
		- (2) BioNetExpander
		- (3) the KG that we have built 
		- (4) MC subgraph finding
		- (5) RWR maybe
		- (6) screencap of our OpenAPI (for the parts we are able to connect to server-side functions by Wednesday) 
		- (7) screencap of UI mockup
	- our plan going forward:
		- (8) show the architecture diagram from the proposal
		- (9) show conceptual diagram of our markov chain approach
	- (10) summary slide for our milestones
NOTE:  the slide deck is actually due on Monday.

- (BT4) Somehow connect BT1 or BT2 (not sure we need both, as one of them will illustrate the point) to the UI mockup

I note that all four of the above items depend on having a relatively complete KG to work with.  Thus we have one final BT item:

- (BT5) Complete knowledge graph so that it has the 21 Q1 diseases, the 8,000 Q1 GCs, the 1,000 Q2 drugs and 1,000 Q2 diseases

Additional nice-to-haves:

- (NTH1) Working OpenAPI connected to script BT1, script BT2, or both
- (NTH2) Movie showing a dry-run of the demo, on screen sharing
