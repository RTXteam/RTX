Here are some coding guidelines for working on ARAX and
[RTX-KG2](https://github.com/RTXteam/RTX-KG2).

# Caveat

Steve Ramsey drafted this document. While the guidelines in the "Performance
Considerations" section were run by David, Eric, and Luis, the "General
Guidelines" as drafted below (while they seem sensible to Steve) have not yet
been discussed by the team. Hopefully this document can be evolved based
on feedback from the team.

# General guidelines

1. Please do not use hard tabs in your code. This can be avoided by configuring
   your editor to insert spaces as needed for proper indentation. See
   [PEP8](https://peps.python.org/pep-0008/).  Per PEP8 guidelines, for python
   code, please use four spaces per indentation level. Consider configuring
   your editor to visually flag PEP8 compliance issues; the resulting code
   will be easier for others to work with, whose editors flag PEP8 issues.
   
2. Please try to use [PEP 484](https://peps.python.org/pep-0484/) type hints
   wherever possible in your Python code.
   
3. No secrets are to be checked into the project's GitHub code repository.
   (AWS keys, database passwords, ssh keys, etc.)
   
4. If you add a dependency on a python package in some module, generally you
   should add that package to the top-level `requirements.txt` file (or verify
   that the dependency is already documented in the `requirements.txt` file).
   
5. When coding a new feature or fixing a bug, if possible, please consider
   adding a `pytest` unit test to a module (either a new module or an existing
   module) in `RTX/code/ARAX/test`.
   
6. ARAX and RTX-KG2 currently use CPython 3.9 in production; any newer language
   features should be avoided or used with utmost caution (i.e., only if you
   fully understand the implications of that choice for deployment).

7. Only LF (i.e., `\n`) line termination for text files in the repo. Please do
   not commit text files with Windows line termination (CRLF) unless you have
   configured git to automatically convert them to LF line termination.

# Performance considerations

1. Don't parse YAML files at query time. In fact, try to avoid reading any
   configuration files from the filesystem at query time if you can. Config
   files are generally small and can be easily cached in memory; in most cases,
   you're better off loading them at application start-up.

2. Don't retrieve files via `scp` or similarly slow mechanisms, at query time.

3. Don't poll in a loop without using a wait mechanism like `time.sleep`.

4. Avoid using `subprocess.run` or `subprocess.check_call` to perform a task
   (e.g., moving or removing a file) that can be done using a function in the
   `os` or `system` namespace.
   
5. Don't use cross-AWS-region database querying. It is very slow.

6. Don't run the ARAX database manager at query time. 

7. Don't run `kp_info_cacher.refresh_kp_info_caches` at query time. Only
   the ARAX Background Tasker should be doing that.

8. Don't do a task a query time that can (without undue complexity) be done at
   application start-up or by the ARAX Background Tasker.

9. Avoid making RTX-KG2 do tasks at query time that only ARAX needs to be doing.


