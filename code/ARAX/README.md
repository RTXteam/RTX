# Code for the ARAX Pilot software 

This directory contains the core software for the **ARAX** system for
computationally-assisted biomedical knowledge exploration that was built (on top
of our RTX reasoning tool system) by **Team ARA Expand** within the NCATS
Biomedical Data Translator program. For a high-level description of ARAX, ARA
Expand, and the Translator program, please see the
[main RTX repository page](../../../../tree/demo).

## Organization of the ARAX software code

### Subdirectory `ARAXQuery`

Contains the classes for controlling the ARAX components.

### Subdirectory `Documentation`

Contains [technical documentation](https://github.com/RTXteam/RTX/blob/demo/code/ARAX/Documentation/DSL_Documentation.md) of ARAX and the ARAXi domain-specific language.

### Subdirectory `Testing`

Contains scripts for integration testing the ARAX system.

## For ARAX Developers: General software development guidelines

- Care should be taken that the code never just dies because then there is no feedback about the problem in the API/UI
- Use the response.error mechanism. Always set up a response object and always return it
    - `DEBUG`: Only something an ARAX team member would want to see
    - `INFO`: Something an API user might like to see to examine the steps behind the scenes. Good for innocuous assumptions.
    - `WARNING`: Something that an API user should sit up and notice. Good for assumptions with impact
    - `ERROR`: A failure that prevents fulfilling the request. Note that logging an error may not halt processing. Several can accumulate
- In your code, do not assume a particular location for the "current working directory". In general, try to use `os.path.abspath` to find
the location of `__FILE__` for your module and then construct a relative path to find other ARAX/RTX files/modules.

General response paradigm:
- Major methods (not little helper ones that can't fail) and calls to different ARAX classes should always:
	- Instantiate a `Response()` object
	- Log with `response.debug`, `response.info`, `response.warning`, `response.error`
	- Place returned data objects in the `response.data` envelope (`dict`)
	- always return the `response` object
- Callers of major methods should call with `result = object.method()`
- Then immediately merge the new result into active response
- Then immediately check `result.status` to make sure it is `'OK'`, and if not, return response or take some other action for method call failure

- The class may store the `Response` object as an object variable and sharing it among the methods that way (this may be convenient)

