# Procedure for ARAX maintenance

##### Stephen Ramsey, March 23, 2026

## Who is this document for?
This procedure is _primarily_ intended for use by Ramsey Lab team members working
on maintenance of the ARAX system; it is specialized for the parts of the ARAX
system that the Ramsey Lab team members are likely to work on (Expand, Resultify,
NodeSynonymizer, etc.). However, much of the content may also be useful for 
other developers working on ARAX (and those non-OSU team members can skip over the 
process steps and suggested coding standards described in this document that 
don't apply to them or the parts of ARAX that they work on).

## Preparing your local dev computer to maintain ARAX
To efficiently maintain ARAX, it is essential to have a local development system that you don't have
to `ssh` into. You will need to have Linux or macOS (though Linux running on Windows via WSL2 is also probably
fine); either `x86_64` or `ARM64` architecture is probably fine (the parts of ARAX that the Ramsey
Lab maintains seem to work fine on both architectures). Your local development computer should have:

- 200 GiB of free disk space
- 32 GiB of memory
- python3.12 installed (with the `venv`, i.e., virtualenv, module available in it)
- Internet (access to the OSU address space via VPN is only required for certain steps late in the process)
- a mainstream web browser installed (Chrome/Firefox)
- tools that need to be installed, by Homebrew or apt or similar: bash, curl, OpenSSH, git, jq, yq
- OSU VPN access (in order to be able to `ssh` into `arax.ncats.io` from off-campus) from your local dev computer

Further, you will need:
- write access to the ARAX GitHub project area (`RTXteam/RTX.git`)
- ssh access to `arax-databases.rtx.ai` as user `ubuntu`
- ssh access to `araxconfig.rtx.ai` as user `araxconfig`
- ssh access to `arax.ncats.io`
- ssh key installed on GitHub so you can clone and commit over `ssh`

It's also helpful to have basic network troubleshooting utilities like
`netstat`, `nc`, etc., installed.

### Setup of your local dev system 
You only need to perform this "setup" procedure once; you don't need to do it
each time you work on a new ARAX issue. You will, however, need to carry out this
procedure after each major new release of ARAX databases.

1. Inspect the shell script 
[`generate-db-symlinks.sh`](https://github.com/RTXteam/RTX/blob/master/code/generate-db-symlinks.sh)
and, from it, compile a list of all the files referenced in that script (each of them is
an "ARAX database" of some kind or other). Download all the ARAX databases on
the list that you compiled, to your development machine, to a directory that
you choose (but which will be persistent across ARAX issues); we'll call that
directory `DB_DIR` (assume `DB_DIR` is an absolute path to the directory you
chose). Then underneath `DB_DIR`, there should be subdirectories like `KG2.10.2`,
`KG2.10.0`, and `KG2.8.0` (the latter is to hold the COHD database which hasn't been
refreshed in a very long time).
```
mkdir DB_DIR
mkdir DB_DIR/KG2.10.2
mkdir DB_DIR/KG2.10.0
mkdir DB_DIR/KG2.8.0
```
To download the databases, you would need
ssh access to `arax-databases.rtx.ai` as user `rtxconfig`; but if you do not have that,
as long as you have ssh access to `arax-databases.rtx.ai` as user `ubuntu`, you can 
log in as `ubuntu` and configure ssh access as user `rtxconfig`, for yourself, like this:
```
scp ~/.ssh/id_ecdsa.pub ubuntu@arax-databases.rtx.ai:
ssh ubuntu@arax-databases.rtx.ai
sudo sh -c 'cat id_ecdsa.pub >> /home/rtxconfig/.ssh/authorized_keys'
sudo chown rtxconfig:rtxconfig /home/rtxconfig/.ssh/authorized_keys
sudo chmod 600 /home/rtxconfig/.ssh/authorized_keys
```
Then you can download files like this:
```
mkdir DB_DIR/KG2.10.2
scp -C rtxconfig@arax-databases.rtx.ai:KG2.10.2/node_synonymizer_v1.0_KG2.10.2.sqlite DB_DIR/KG2.10.2/
```
After downloading the databases, the `DB_DIR` directory structure would
look like this:
```
DB_DIR/KG2.10.0
DB_DIR/KG2.10.0/xcrg_decrease_model_v1.0.KG2.10.0_new_version.pt
DB_DIR/KG2.10.0/xcrg_increase_model_v1.0.KG2.10.0_new_version.pt
DB_DIR/KG2.8.0
DB_DIR/KG2.8.0/COHDdatabase_v1.0_KG2.8.0.db
DB_DIR/KG2.10.2
DB_DIR/KG2.10.2/node_synonymizer_v1.0_KG2.10.2.sqlite
DB_DIR/KG2.10.2/kg2c_v1.0_KG2.10.2.sqlite
DB_DIR/KG2.10.2/ExplainableDTD_v1.0_KG2.10.0_refreshedTo_KG2.10.2.db
DB_DIR/KG2.10.2/chemical_gene_embeddings_v1.0.KG2.10.0_refreshedTo_KG2.10.2.npz
DB_DIR/KG2.10.2/autocomplete_v1.0_KG2.10.2.sqlite
DB_DIR/KG2.10.2/curie_ngd_v1.0_KG2.10.2.sqlite
DB_DIR/KG2.10.2/curie_to_pmids_v1.0_KG2.10.2.sqlite
DB_DIR/KG2.10.2/fda_approved_drugs_v1.0_KG2.10.2c.pickle
```
To get your list of database files, check `generate-db-symlinks.sh` since that script
should have the
latest list of database dependencies.

2. On your local dev system, create a directory for your ARAX development work; you can 
call it whatever you want, but in this document we will denote the directory's
absolute path by `ARAX_DEV_DIR`. You will need to install the script
`generate-db-symlinks.sh` into that directory and make it executable:
```
cd ARAX_DEV_DIR
curl -o generate-db-symlinks.sh -s -L \
  https://raw.githubusercontent.com/RTXteam/RTX/refs/heads/master/code/generate-db-symlinks.sh
chmod a+x generate-db-symlinks.sh
```
Note, if you are actually _working on a new ARAX database release_, that will
involve customization of the aforementioned script; but that kind of work is
beyond the scope of this procedure document which is for more routine
maintenance.

3. Create a file `ARAX_DEV_DIR/flask_config.json` containing the following JSON:
```
{
    "port": 5001,
    "check_databases": false,
    "run_background_tasker": false,
    "force_disable_telemetry": true,
    "query_fork_mode": false
}
```

4. Make sure you have ssh access to `araxconfig@araxconfig.rtx.ai`. You need
to set up the ssh public key exchange and put your public key in the 
file `/home/araxconfig/.ssh/authorized_keys` on `araxconfig.rtx.ai`,
and you should do a test login to araxconfig.rtx.ai using this ssh key,
```
ssh araxconfig@araxconfig.rtx.ai
```
to ensure that the IP address for `araxconfig.rtx.ai` is in your
`~/.ssh/known_hosts` file.

Once you done with these steps, you are ready to work on a maintenance task for ARAX;
continue with the procedure in the next section, which you should follow (from
that section's beginning) for each ARAX maintenance task that you work on.
For extensive documentation on the `flask_config.json` file schema, see
the [relevant section of the ARAX wiki](https://github.com/RTXteam/RTX/wiki/Config,-databases,-and-SFTP#flask_configjson).

### Potential gotcha: TCP port
It is possible that TCP port 5001 is aready in use on your computer, by some
other running process. If so, you will get an error when you try to start up ARAX
and you'll need to change the port number in your `flask_config.json` file
to some other number (say, "5002") and remember to change "5001" to "5002" wherever
you see it in the instructions below). To see if port 5001 is already in use, you 
could run
```
netstat -an | grep tcp | grep ':5001'
```
and see if you get any results. 

## Per-task procedure for ARAX maintenance 

1. Expectations for bug reporting in ARAX
 If you
   have a query graph (JSON or ARAXi/DSL) that you were running when you 
   encounter a bug, it is _vital that you paste the JSON or ARAXi into the issue_.
   In the issue, you should also describe what happens when the JSON or ARAXi
   query graph is run through ARAX, that is not correct/expected behavior.
   This is essential so that the maintainer can know whether or not they have
   successful reproduced the bug. Please include information such as:
   - The ARAX host that you ran your query on
   - The date/time (including timezone) when you ran your query
   - If you have it, the relevant excerpt from the ARAX ".elog" file (`/tmp/RTX_OpenAPI_DEVAREA.elog`), where
   `DEVAREA` is one of `beta`, `test`, `devED`, `devLM`, `shepherd`, etc.
   - Screencaps of any relevant information that you are seeing in the ARAX User Interface.
   - Relevant excerpts of the message log from ARAX, which you may be able to get through the
     ARAX User Interface (depending on the severity of the bug).
     
2. If no one has done so already, create a GitHub issue in the 
   [`RTXteam/RTX` issue tracker](https://github.com/RTXteam/RTX/issues). In the issue
   metadata in GitHub, under "Type", select `bug`, `feature`, or `task`, as appropriate.
   Further, under "Labels", select "High Priority" if you know that it is a high-priority
   issue.  Often, maybe a third of the time, there is a "parent issue" in some
   other GitHub project area (e.g., [NCATSTranslator/Feedback](https://github.com/NCATSTranslator/Feedback/)) 
   that documents an
   issue someone saw in the Translator UI, that has been traced to ARAX. It is
   vital that the two issues reciprocally hyperlink one another: in the
   `RTXteam/RTX` issue, the parent issue (i.e., the one in
   `NCATSTranslator/Feedback` or wherever) should be hyperlinked (with some comment
   like "cross-post status updates in the parent issue here:", and in the parent
   issue, the RTXteam/RTX issue needs to be hyperlinked (with some comment like
   "ARAX team is working on this; for the latest status, check here:"). If you
   are claiming an issue in the issue tracker, _you should assign it to yourself_
   so that others will know that the issue has been claimed. Feel free to tag
   others whose input you want, via a comment, or, where you are confident that
   it is appropriate, co-assigning them to the issue (in which case, make it 
   clear in the issue comment that you are taking the lead on working on the issue).

3. Create a branch called `issue-XXX` to work on the issue (where `XXX` is the issue
   number). In most cases, you will want to branch off of `master`, but in rare
   cases, the `issue-XXX` branch might need to be branched off of another
   (non-master) branch, for example, if you are addressing an issue with a
   feature in ARAX that is not yet merged to master but is only present within
   some other feature branch (note, this is highly unusual). In the `RTXteam/RTX`
   issue, add a comment noting the branch that you are working on, with a
   message like "Working on this issue in new branch `issue-XXX`."

4. On your development machine, in the `ARAX_DEV_DIR` directory, 

- create a new folder `issue-XXX` to work in this issue; `cd` into it
- clone the ARAX GitHub project area code into that directory; 
- create a python3.12 virtualenv called `venv`
- install ARAX's distribution package dependencies (for both running ARAX,
which is `requirements.txt`, and analyzing ARAX code, which is `dev-requirements.txt`) 
into the `venv` virtualenv; 
- run the 
`generate-db-symlinks.sh` script in order to set up the database
symbolic links (do it EXACTLY as shown, and with your CWD being 
_in the issue directory_ `issue-XXX`); 
- copy the `flask_config.json` file
to the `RTX/code/UI/OpenAPI/python-flask-server/openapi_server` subdirectory;
- and, finally, generate the KP info cache for ARAX-expand.

Here are the steps:
```
cd ARAX_DEV_DIR
mkdir issue-XXX && cd issue-XXX
git clone -b issue-XXX git@github.com:RTXteam/RTX.git
python3.12 -m venv venv
venv/bin/pip install -r RTX/requirements.txt
venv/bin/pip install -r RTX/dev-requirements.txt
../generate-db-symlinks.sh
cp ../flask_config.json RTX/code/UI/OpenAPI/python-flask-server/openapi_server/
venv/bin/python -u -m RTX.code.ARAX.ARAXQuery.Expand.kp_info_cacher
```
After each command (_especially_ the `pip install` commands), make sure you look for
successful completion before issuing the next command in the above list.

The last command (the one to build the KP info cache), if it completes
successfully, should produce this final line of output:
```
The process with process ID 61928 has FINISHED refreshing the KP info caches
```

### Special setup procedure if you are working on Legacy-ARAX
If (and _only if_) you will be working on an issue with "Legacy-ARAX" (TRAPI 1.5.0), 
you will want to configure ARAX to query legacy KP endpoints. You do that by editing
the module `RTX/code/ARAX/ARAXQuery/Expand/kp_info_cacher.py` and changing the line of code
```
self.forced_kp_version = '1.6.0'
```
to
```
self.forced_kp_version = '1.5.0'
```
Make _sure_ you do not accidentally commit this code change in `kp_info_cacher.py` to the ARAX
branch; it is just used as a local configuration change for development work (yes, it could
eventually be made a proper configuration option).

## Running ARAX locally on your development computer
Assuming you have completed all the steps in the seciton "Per-task procedure for
ARAX maintenance", you should be ready to run ARAX locally on your development computer.

### Verify that your branch is in a "known good" state.
Before doing any development work, you should test ARAX to make sure it can run
queries with the code that you currently have in the `issue-XXX` branch (which should
at this point be the same as the code at the head of the `master` branch). This is done
in two steps: running the unit test suite and then running the example queries through the
ARAX Flask server locally.

#### Running the ARAX unit tests
Running the unit tests involves these steps:
```
cd ARAX_DEV_DIR/issue-XXX/RTX
../../../venv/bin/pytest --cache-clear -v
```
The procedure will take about 15 minutes to complete. All standard unit tests should pass, or your
locally installed ARAX is not in a "known good" state (and you should work on troubleshooting
the broken unit test before proceeding). 

#### Running the example queries in the ARAX flask server locally
1. Start the flask server locally, _exactly_ as follows:
```
cd ARAX_DEV_DIR/issue-XXX/RTX/code/UI/OpenAPI/python-flask-server
../../../../../venv/bin/python -u -m openapi_server
```
The output in your terminal session should look something like this:
```
sramsey-laptop:python-flask-server sramsey$ ../../../../../venv/bin/python -u -m openapi_server
Loading overly general concepts node file: /Users/sramsey/Documents/Work/Proj/translator-performance-phase/ARAX/issue-2703/RTX/code/ARAX/ARAXQuery/Filter_KG/../../KnowledgeSources/general_concepts.json
Successfully loaded the blocklist file
Using JSON provider: CustomJSONProvider
Starting flask application with TCP port: 5001
 * Serving Flask app '__main__'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
 * Running on http://10.197.154.29:5001
Press CTRL+C to quit
```
2. In a different window, run your web browser (Firefox or Chrome), and using the "File" menu, select
"Open File...", and in the dialog box, navigate to `ARAX_DEV_DIR/issue-XXX/RTX/code/UI/interactive` and
select `index.html`. Now, in the ARAX User Interface page that renders in your browser, you will see an orange banner message appear, saying "Call to /meta_knowledge_graph failed; could not load predicates and node categories."; do not worry about that banner message, that is expected when
you first load `index.html` on your local development computer, because the base URL for querying
the ARAX back-end is not (yet) configured via Settings (see Step 3). Just click the "x" to 
delete the orange banner message.
3. On the navigation pane on the left-hand side, click on the `Settings`, 
and then change the "ARAX QUERY URL" textbox to contain _exactly_ this string:
```
http://localhost:5001/api/arax/v1.4/query 
```
and click "update" (you may well have to widen your browser window to see the
blue "update" button, which is to the right of the text box).
4. In the navigation pane in the ARAX User Interface in your web browser, click on 
`Query`, click on `JSON`, and click on `Example 1` (it's a tiny orange link just above 
the large empty text-box). Then click on "Post to ARAX". Compare the results that
are listed under the "Results" navigation tab, to what you would see if you ran the 
`Example 1` JSON query on `arax.ncats.io/test` or `arax.ci.transltr.io`. Repeat this
procedure for `Example 2`, `Example 3`, and `Pathfinder`. 
5. Click on the "Results" tab (on the left) and scroll down to look at the results. The results don't have to
be _exactly_ the same as what you see with the `master` branch code, but if you see any _major_ 
unexpected differences, please report an issue (e.g., via the `#deployment` channel in the 
`CATRAX` Slack workspace) before proceeding; the reason for this
is that if you aren't starting with a "known good" ARAX, it doesn't make sense to
try to do new development. The exception to this guidance is if one of the standard
KPs has suddenly broken one of the example queries in ARAX; in that case, we wouldn't
expect the above tests to yield a successful result (and, in fact, it is essential
to observe the _failing_ example query before proceeding so we know we have
reproduced the problem). But the case of a KP breaking one of our example queries
is quite rare, so we will not address that scenario further in the procedure
that follows. 
5. Click on the "Messages" tab (on the left) and scroll down to look at the TRAPI message
log. If you are running ARAX locally on a development system, you will see one TRAPI
warning for sure:
```
WARNING:    Not saving response to S3 because I don't know the S3BucketMigrationDatetime
```
That is expected when you are testing ARAX on your local computer; don't worry about it.
But any other TRAPI warning or error messages are a reason to compare the TRAPI message 
log from your branch, with the TRAPI message log that results when you run with the ARAX
code from the `master` branch.

#### Note on testing if you are working on Shepherd-ARAX
If you are doing work on "Shepherd-ARAX", then you should
first run the unit tests and example queries with `self.forced_kp_version = '1.5.0'`, and then set 
`self.forced_kp_version = '1.6.0'` for your development/testing work; this is because many unit tests
will probably not (yet) pass, if ARAX is only querying `infores:retriever`.
Also, if you are working on Shepherd-ARAX, when you reach the point of
testing in an `arax.ncats.io` dev-area, you should test on
`arax.ncats.io/shepherd` and not `arax.ncats.io/beta`; this is because
`arax.ncats.io/shepherd` is already set up for `self.forced_kp_version = '1.6.0'`
and the KP info cache is already set up for `infores:retriever`. The instructions
below assume you are not working on an issue that is specific to
Shepherd-ARAX.

### If you have been assigned a bugfix, reproduce it locally on your dev system
If your `issue-XXX` is a bug report that you or someone else has contributed, 
then you'll want to make sure you can reproduce the bug using your locally 
running ARAX. It is _very hard_ to debug ARAX issues on a remote endpoint, so
even if it takes some effort, it is generally advantageous to figure out how
to reproduce the bug on your local development system. Often, this is just
a matter of running the query graph JSON (or ARAXi) submitted with the issue.
If you are aiming to work on an ARAX bug, and if you can't reproduce the issue
locally on your development computer, ask for help before proceeding.

## Consider writing a unit test for the bug or feature you are working on
If possible, write a new unit test to exercise the bug (or not-yet-implemented
feature) on your dev system (this is sometimes not reasonably possible, but if
it is straightforward to do it, you are encouraged to do it). Unit tests go in the
`RTX/code/ARAX/test` directory.  This would provide a durable benefit for the
project since any regression of that test case (e.g., due to future development
work) will be detected.

## Check your code modules before working on them
Before working on any ARAX module, e.g., `foo.py`, run it through these checks
```
ruff check foo.py
mypy --ignore-missing-imports foo.py
pylint foo.py
```
to assess code quality and type-correctness at baseline. If there are 
minor "spot" issues, you can fix them. If there are major issues, please
reach out for help to discuss how to proceed. Having these checks pass
before you implement your bugfix or feature enhancement is critical for
enabling these static analysis tools to catch errors that might be introduced
as a _side effect_ of your bugfix or feature enhancement.

## Code your bugfix or feature enhancement
Any module `foo.py` that you work on, should pass static code checks 
_before you commit to your branch_:
```
ruff check foo.py
mypy --ignore-missing-imports foo.py
pylint foo.py
```
where, in the case of pylint, "clean" means a score of at least 9.50. When 
maintaining legacy ARAX modules, it is OK to disable certain pylint errors 
via a comment if it is simply infeasible to fix (e.g., when pylint complains
that the `ARAX_expander.py` module is too long, shortening that module is
beyond the scope of typical bugfix and feature development work). 
There should be no errors from `ruff` or `mypy`. If you have JSON or YAML
files that you have edited or added for your work on issue-XXX, you should
syntax-check the JSON or YAML file with `jq` or `yq`.

## Coding guidelines
Apart from the requirements (already stated above) regarding static code checks
for PEP8 compliance, type checking, and linting, there are some additional 
guidelines for coding changes on the ARAX code-base:
1. If you are adding or modifying a line of code for debugging that will need 
to be removed or updated before you commit, make _sure_ you add a line comment
`# :DEBUG:`. This is important so you can ensure that debugging code doesn't
leak through into the commit.
2. Please use modern type hints (from python3.10 or newer), so no uppercase
`Dict` or `List`, and make sure to use `| None` instead of `Optional`. 
3. Please review your code with a code LLM (e.g., Claude code or Copilot) to check for bugs before committing. Best results from LLM review seem to be when the LLM can see the code diffs in the context of the full ARAX code-base.
4. Please visually inspect every line of your code diffs with `git diff` 
before committing; this is the perfect opportunity to catch debug code 
(which would be indicated with a `# :DEBUG:` line comment) before it gets 
accidentally committed.
5. If you update the code in a function, it is best practice to bring it up 
to modern standard in terms of type hinting and PEP8 formatting. But be
cautious about entirely reformatting (such as with `black` or whatever) 
a whole module for which another active-contributing team member has the 
vast majority of commits; check with her/him before making a major reformat.
6. If your code update introduces a new dependency on a PyPI distribution
package, it is critical that you update the ARAX `RTX/requirements.txt` file
with the version-pinned dependency. You then need to _test_ the updated
`requirements.txt` file, using `venv/bin/pip install -r RTX/requirements.txt`, 
to make sure it works as modified. If your code update introduces a dependency
on a mypy types package like `types-requests` or whatever, you need to put
that in `RTX/dev-requirements.txt` as a pinned dependency and test it with `pip`.
7. All newly contributed python code from the OSU team should adhere to the [PEP8 Style Guide for
   Python Code](https://peps.python.org/pep-0008/). Among other things, this means: No hard tabs; four space indentation;
   max 79 characters per line; proper use of CamelCase or snake_case or CAPS_SNAKE_CASE;
   proper use of whitespace around infix operators; etc.
8. Where possible, try to minimize use of "path surgery", i.e., `sys.path.append`.
_Some_ path surgery is inevitable given the bifurcation of the code-base into
`RTX/code/UI/OpenAPI/python-flask-server` and `RTX/code/ARAX` subtrees, but please
try to minimize it, bearing in mind that ARAX is run using `python -m` so it should be
able to interpret dotted imports like `from openapi_server.models.node import Node`.

## Commit to your branch
Do not commit to the `master` branch; at this point, you should commit your
bugfix or new feature code, to your `issue-XXX` branch.
When committing, you should _tag the issue number in the git commit message_. 
You should also put a comment in the GitHub
issue, just after your commit, indicating whether the commit is (or is not) 
expected to be a complete fix (basically a one-line status report).
The commit procedure is simple, assuming your local `issue-XXX` branch is
not behind the `issue-XXX` branch on the remote (which would be very unusual
given how issue-specific development work on ARAX is typically done):
```
git commit -m '#XXX' module1.py module2.py module3.py
git push origin issue-XXX
```
Do not push your code to the `master` branch at this point.

## Test on a `arax.ncats.io` dev-area
You'll now want to test your code on `arax.ncats.io`, on one of the available 
development "devareas" (`/beta`, `/test`, etc.). The steps below assume you'll
be testing in `/beta`. The procedure is as follows:
1. Put a message on the `#deployment` channel in the `CATRAX` Slack
workspace, that you are 
"Working on `arax.ncats.io/beta`, for ARAX issue XXX".
Wait at least 10 minutes for someone to respond. If there are no objections, 
proceed:
2. `ssh arax.ncats.io`
3. `sudo docker exec -it rtx2 bash`
4. `su - rt`
5. `cd /mnt/data/orangeboard/beta/RTX`
6. `git status`<br />
Note the branch and whether there are local changes. If the local `RTX` code is not
currently on the `master` branch, and/or if there are locally modified modules
or config files (not counting untracked files), then someone else is _probably
already using `arax.ncats.io/beta` for testing, and you should _reach out before
proceeding_. Only proceed if there are no locally modified tracked files and
the local code repository is on `master`. Staying in the same `RTX` directory:
7. `git fetch origin`
8. `git checkout issue-XXX`
9. `git pull origin issue-XXX`
10. Run all the pytests, using your updated code: `cd RTX && pytest -v --cache-clear`<br />
All standard ARAX unit tests should pass, when run in the `arax.ncats.io/beta` devarea.
11. Next is to run the example queries, using your updated code. You will need to restart ARAX. 
Exit out of the shell session for user `rt`,
by typing `exit`. You should see the root account prompt `#`:
12. Stop ARAX:  `service RTX_OpenAPI_beta stop`
13. Verify that ARAX is stopped: `ps axwf | grep 5003`<br />
If you see any processes with the substring "5003" in the process title (which identifies
them as coming from the `/beta` devarea), you should kill them with `kill -9 PID`.
14. Start ARAX: `service RTX_OpenAPI_beta start`
15. Follow ARAX start-up: `tail -f /tmp/RTX_OpenAPI_beta.elog`
You will know that ARAX is ready when you see this in the `.elog` file:
```
2026-03-24T02:02:06.369294: INFO: ARAXBackgroundTasker: Completed meta KG refresh successfully
```
and you don't see a stacktrace or other obvious error message.
16. Go to your web browser and navigate to `https://arax.ncats.io/beta` and run the
Example 1, Example 2, Example 3, and Pathfinder queries and verify that
they completed successfully. If a pytest fails or one of the example queries fail,
do not continue on this checklist; you need to debug the issue.

## Create a pull request for merging your issue branch into master
1. Open a Pull Request (for merging `issue-XXX` into `master`)
for your issue and enter a succinct description of the
issue in the pull request. Add a comment in issue `XXX` linking the PR.
Via comments in the pull request, indicate that your 
updated modules passed ruff, mypy, and pylint checks, and that the unit tests
and example queries passed on `arax.ncats.io/beta`. Assign someone to review the
pull request. In the `issue-XXX` issue in GitHub, under "Labels", select
"Waiting for PR review".
2. Check back 15 minutes after you opened the PR, to see if GitHub's static checks
flagged an issue. If there is an issue, fix it before merging.
3. In the PR page on GitHub, assign Copilot as a reviewer, and fix (or document why not fixing) any issues it raises. Sometimes Copilot raises "security issues" that are not relevant because, for example, they are related to debug messages in our unit tests. Nevertheless, Copilot does catch bugs and it is worth running.
4. Once the PR is approved, give a warning message on `#deployment` 
("Merging PR XXY for issue XXX, to ARAX master branch"). If it is a large merge
or with particular risk for impacts on ARAX in CI, consider also messaging
the `#arax-alerts` channel in the `NCATSTranslator` Slack workspace, a message that
there will be a restart of ARAX in CI, with new code.
5. Merge the PR, by using the green "Merge pull request" button in GitHub. 
A warning about the GitHub tool for managing merge conflicts:
it _only modifies the parent branch_, which is fine if you are merging `issue-XXX` into
`master`, but in situations where you want to merge `master` into an issue branch,
this can have bad unintended consequences. DO NOT EVER USE THE GITHUB MERGE TOOL FOR
FIXING CONFLICTS FOR A MERGE FROM MASTER INTO AN ISSUE BRANCH!

## Post-merge testing
1. Message the `#deployment` channel in the `CATRAX` Slack workspace that you
are doing work on `arax.ncats.io/beta`; on the `arax.ncats.io` system, inside the `rtx2` container, in
the `/mnt/data/orangeboard/beta/RTX` directory, switch back to the `master` branch
and restart ARAX:
```
ssh arax.ncats.io
sudo docker exec -it rtx2 bash
su - rt
cd /mnt/data/orangeboard/beta/RTX
git fetch origin
git checkout master
git pull origin master
exit
```
Now you are `root` with the `#` prompt:
```
service RTX_OpenAPI_beta stop
service RTX_OpenAPI_beta start
tail -f /tmp/RTX_OpenAPI_beta.elog
```
If you had to fix merge conflicts or if your issue
branch was behind `master` when you merged, rerun all the pytests. 
In any case, you will need to test the ARAX User Interface again with the
Example 1 query. If everything is working, then proceed.
2. Change your local `ARAX_DEV_DIR/issue-XXX/RTX` code branch to the
`master` branch:
```
cd ARAX_DEV_DIR/issue-XXX/RTX
git fetch origin
git checkout master
git pull origin master
```
3. An hour after merging your PR, check the ARAX Test Build (CI/CD test suite) 
in GitHub, to ensure it ran successfully.
4. Test your bugfix or new feature, if possible, on `arax.ci.transltr.io`.
If ARAX does not come back up on `arax.ci.transltr.io` within 15 minutes of
your merge, ask for help on `#deployment`.
5. Check on Slack and in GitHub notifications, to see if there have been any 
reports of problems on ARAX in CI or on `arax.ncats.io/beta`, since you
merged your PR for your issue.

## Final clean-up
1. In GitHub, delete the `issue-XXX` branch and add a comment in the issue
indicating "Branch `issue-XXX` deleted." Note, do not delete the branch
so early that it causes the "Test Build" to fail. Make sure you verify
that the Test Build has completed before you delete the issue branch.
2. Update the [ARAX ChangeLog issue](https://github.com/RTXteam/RTX/issues/2515) 
(by editing the top comment in the issue) giving a succinct description of
your "fix" for `issue-XXX` and tagging the issue with `#XXX`.
3. Add an item for the next [ARAX All-Hands Meeting agenda](https://docs.google.com/document/d/1SHMwq1aiqgUmBWhb6c_vHGH8G3VF6ssvL2vlhfMwOCg/edit?tab=t.0), 
called "ARAX issue XXX: fix merged".
4. If there is a "parent issue" (e.g., in `NCATSTranslator/Feedback`), add
a comment to that issue indicating that ARAX issue XXX is fixed and merged
to the `master` branch.
This will allow the parent issue stakeholders (e.g., the TAQA team) to rerun 
their test or reproducible example for the issue.
5. Update any documentation (e.g., in the ARAX wiki) relevant to your feature
or bugfix.
6. At the next ARAX all-hands meeting, make sure you are present so you
can give a brief update on the outcome of your work on `issue-XXX`.
7. In the [CATRAX milestones tracker for Year 2](https://github.com/Translator-CATRAX/Y2-CATRAX-Milestones-Repo)
project area on GitHub, in the issue tracker, make sure you find a milestone
that is relevant to your issue and add a comment to that issue, with a
hyperlink to the issue that you worked on, and your `@username` GitHub handle.
This ensures that at the end of the budget period, your work on ARAX issues
will be accounted for (in aggregated summary form) in the progress report
to NCATS.
8. Optionally, delete (on your development system) `ARAX_DEV_DIR/issue-XXX`.
Before deleting, you may wish to save any special testing scripts or JSON query graphs as
attachments in the issue (it is better to attach them to the issue than to 
just leave them in your issue work folder on your development computer).
9. Close issue `XXX` in the ARAX issue tracker. Only do this when all previous
steps are completed. If you are not yet done, indicate how far you got
on the checklist, as a comment in the issue, so you will know where to resume.







