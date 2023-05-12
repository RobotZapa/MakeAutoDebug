# Make Debug

A tool to help with common problems getting your environments running. Containers don't fix everything.
At the moment it is designed and works well on linux. It may require changes to work on windows.

# User guide
## Options

- `makedebug.py` runs with default command (set at the top of the file)
- `makedebug.py -r <command>` run fixes related to specific command
- `makedebug.py -f <fix_name_1>,<fix_name_2>` run a single or group of listed fixes
- `makedebug.py -o <fix_name_1>,<fix_name_2>` omit a single or group of listed fixes
- `makedebug.py -u` (program does not run) updates and overwrites the fixes in the script from the url
- `makedebug.py -l` (program does not run) list all fixes and commands
- `makedebug.py -d <fix_name_1>` (program does not run) documentation for the fix
- `makedebug.py --doc` (program does not run) documentation specific to your file
- `makedebug.py -h` (program does not run) help

## Status Codes
- `FIXED` - test ran and completed successfully
- `FAILED` - test ran and completed unsuccessfully
- `NO ISSUE` - test was checked for and deemed not required
- `TIMEOUT` - test was not detected within it's timeout
- `UNKNOWN` - test status is unknown
- `ERROR` - test was caught with an exception (will generate an error.log file)

# Dev Guide

## Fix decorator

### Signal arguments

- Not having `ERROR` signal will collect and detect from STDOUT
- `ERROR` will only collect and detect from STDERR
- `BLOCKING` will issue a ctl-c termination of the program before running the fix and starting it back up after
- `DEPEND` will run before the command
- `INSPECT` will run after the fixes complete
- `TERMINAL` will end running all fixes terminate the program and provide the run table if return True
- `UNTIL` will trigger (more than once) any time it's detect criteria is met until it returns True

### Keyword arguments

- `detect` text or list of text (in order) to be detected
- `timeout` from the initial startup of the program to the time the fix is no longer relevant (default 300 seconds)
- `command` list of commands this will run for (will run for all commands if not present)
- `tell` information to be displayed with the table on fix FIXED status
- `note` information to be displayed with the table on NO ISSUE/TIMEOUT status
- `warn` information to be displayed with the table on UNKNOWN status
- `fail` information to be displayed with the table on FAILED status
- `info` information to be displayed with the table on TBD status (when option -l is used)

### Return values and status

These only apply to `DEPEND` and `INSPECT` fixes as they have no `detect` that would auto generate a run status
- True - FIXED
- False - FAILED
- None - NO ISSUE

### Notes

A terminal is good but not required. Without one, it will simply wait for timeout of all tests; however, that timeout is 
reset by any other test running. Default timeout is set at the top of the file.

There is a limitation at the moment that prevents more than one fix from being triggered by the same line of output with
detect.