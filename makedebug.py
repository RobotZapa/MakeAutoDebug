"""
Copyright 2023 Michael Elliott - MIT License
doc string for info about this makedebug.py script
"""
import getopt
import inspect
import sys
import subprocess
import time
import os
import sys
import traceback
import urllib.request
import __main__

UPDATE_URL = ''  # todo your update url here
DEFAULT_PATH = './'  # todo your default path here
DEFAULT_COMMAND = 'python3 test_command.py'  # todo your default command
DEFAULT_TIMEOUT = 300
DEFAULT_LOG_FILENAME = 'error.log'

DEPEND = 'depends'  # runs before the process begins
INSPECT = 'inspect'  # runs after all fixes have completed
TERMINAL = 'terminal'  # exit(0) the program if true
BLOCKING = 'blocking'  # exits the process, then runs fix, then restarts and continues looking for problems
ERROR = 'stderr'  # looks in standard error
UNTIL = 'until'  # retriggerable until True is returned todo implement this and write a test


class Fix:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.timeout = kwargs['timeout'] if 'timeout' in kwargs else DEFAULT_TIMEOUT
        self.command = kwargs['command'] if 'command' in kwargs else ''
        self._detect = kwargs['detect'] if 'detect' in kwargs else None
        self._detect_copy = kwargs['detect'][:] if 'detect' in kwargs else None
        self.until = True if UNTIL in args else False
        self.blocking = True if BLOCKING in args else False
        self.terminal = True if TERMINAL in args else False
        self.triggered = False
        self.floating = True
        self.status = 'TBD'

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Do something with the function here
            self.triggered = True
            return func(*args, **kwargs)
        wrapper.__doc__ = func.__doc__
        return wrapper

    def set_val(self, value):
        if self.until:
            if value is True:
                self.status = 'FIXED'
                self.triggered = True
                self.until = False
            else:
                self.status = 'FAILED'
                self.triggered = False
                self._detect = self._detect_copy[:]
            return
        if value is True:
            self.status = 'FIXED'
        elif value is False:
            self.status = 'FAILED'
        else:
            self.status = 'UNKNOWN'

    def message(self):
        if self.status == "FIXED":
            return self.kwargs['tell'] if 'tell' in self.kwargs else ''
        elif self.status in ("NO ISSUE", "TIMEOUT"):
            return self.kwargs['note'] if 'note' in self.kwargs else ''
        elif self.status == "UNKNOWN":
            return self.kwargs['warn'] if 'warn' in self.kwargs else ''
        elif self.status == "FAILED":
            return self.kwargs['fail'] if 'fail' in self.kwargs else ''
        elif self.status == "TBD":
            return self.kwargs['info'] if 'info' in self.kwargs else ''
        return ''

    def detect(self, line):
        if self._detect:
            if type(self._detect) == list:
                while self._detect[0] in line:
                    value = self._detect.pop(0)
                    if len(self._detect) == 0:
                        return True
                    line = line[line.index(value):]
            elif type(self._detect) == str:
                return self._detect in line
            self.status = 'NO ISSUE'
        elif self._detect is None:
            return True
        return False


#####################
# v DROP IN FIXES v #
#####################


@Fix(DEPEND, command="python3 test_command_2.py", info='TEST SUCCESS')
def info_and_docstring_test(path, command):
    """
    DOCSTRING TEST SUCCESS
    """
    return True


@Fix(DEPEND, command='python3 test_command.py', tell="TEST SUCCESS", note="TEST FAIL")
def command_positive_test(path, command):
    return True


@Fix(DEPEND, command='python3 test_command_2.py', note="TEST SUCCESS", fail="TEST FAIL")
def command_negative_test(path, command):
    return False


@Fix(DEPEND, info='INFO TEST SUCCESS', tell='TEST SUCCESS')
def depend_test(path, command):
    open("start.fix", "w+").close()
    open("until.fix", "w+").close()
    return True


@Fix(UNTIL, detect=['BEFORE', 'AFTER'], tell='TEST SUCCESS')
def until_test(path, command):
    ret = False
    if os.path.isfile('until.fix'):
        os.remove('until.fix')
        ret = True
    open('until.fix', 'w+').close()
    return ret


@Fix(detect=['waiting', 'generic.fix'], tell='TEST SUCCESS')
def generic_test(path, command):
    open("generic.fix", "w+").close()
    return True


@Fix(BLOCKING, detect='blocking...', tell='TEST SUCCESS')
def blocking_test(path, command):
    open("blocking.fix", "w+").close()
    return True


@Fix(ERROR, detect='error.fix not present', tell='TEST SUCCESS')
def error_test(path, command):
    open("error.fix", "w+").close()
    return True


@Fix(detect='AFTER timeout.fix', timeout=5, note="TEST SUCCESS")
def timeout_triggered_test(path, command):
    return None


@Fix(detect='AFTER timeout.fix', timeout=15, tell="TEST SUCCESS")
def timeout_not_hit_test(path, command):
    return True


@Fix(TERMINAL, detect=['READY', 'TERMINAL'], note='TEST SUCCESS')
def terminal_test(path, command):
    return True


@Fix(INSPECT, tell='TEST SUCCESS', note='TEST FAIL')
def inspect_test(path, command):
    here = os.listdir()
    for file in here:
        if file.endswith('.fix'):
            return False
    return True


@Fix(INSPECT, tell='TEST SUCCESS', warn='TEST FAIL', note="TEST FAIL")
def fixed_test(path, command):
    return True


@Fix(INSPECT, note='TEST SUCCESS', warn='TEST FAIL', tell="TEST FAIL", fail="TEST SUCCESS")
def fail_test(path, command):
    return False


@Fix(INSPECT, warn='TEST SUCCESS', tell='TEST FAIL', note="TEST FAIL")
def unknown_test(path, command):
    return None


#############
# INTERNALS #
#############


def handler(fixes, path, command):
    prerun = [fix for fix in fixes if DEPEND in fix['obj'].args]
    postrun = [fix for fix in fixes if INSPECT in fix['obj'].args]
    errors = [fix for fix in fixes if ERROR in fix['obj'].args]
    standard = [fix for fix in fixes if fix not in prerun + postrun + errors]

    for fix in prerun:
        fix['obj'].set_val(fix['func'](path, command))
    process = None
    while True:
        try:
            process = stdout_handler(standard, path, command, process)
            standard = [fix for fix in standard if not fix['obj'].triggered]
            if process is TERMINAL:
                break
        except BaseException as e:
            traceback.print_exc()
            print(str(e))
        if process is None:
            if not stderr_handler(errors, path, command):
                break
            errors = [fix for fix in errors if not fix['obj'].triggered]
    for fix in postrun:
        fix['obj'].set_val(fix['func'](path, command))


def stdout_handler(fixes, path, command, process):
    if not process:
        process = subprocess.Popen(command, shell=True, cwd=path, stdout=subprocess.PIPE)
    stop = time.time() + max([fix['obj'].timeout for fix in fixes]+[1])
    for i, out in enumerate(process.stdout):
        if time.time() > stop:
            flag_floating(fixes, "TIMEOUT")
            process.terminate()
            return
        if out:
            out = out.decode("utf-8")
        else:
            continue
        print(out)
        for fix in fixes:
            if fix['obj'].terminal and fix['obj'].detect(out):
                if fix['func'](path, command):
                    flag_floating(fixes, "NO ISSUE")
                    return TERMINAL
                fix['obj'].triggered = False
            elif fix['obj'].detect(out):
                if not fix['obj'].triggered:
                    if fix['obj'].blocking:
                        process.terminate()
                        fix['obj'].set_val(fix['func'](path, command))
                        return False
                    else:
                        fix['obj'].set_val(fix['func'](path, command))
                        return process
    process.terminate()


def stderr_handler(fixes, path, command):
    process = subprocess.Popen(command, shell=True, cwd=path, stderr=subprocess.PIPE)
    stop = time.time() + max([fix['obj'].timeout for fix in fixes]+[1])
    try:
        if process.poll() is None:
            process.wait(timeout=stop)
        for line in process.stderr:
            err = line.decode('utf-8')
            for fix in fixes:
                if fix['obj'].detect(err):
                    fix['obj'].set_val(fix['func'](path, command))
                    return True
    except subprocess.TimeoutExpired:
        flag_floating(fixes, 'TIMEOUT')
        return False
    return False


def flag_floating(fixes, status="UNKNOWN"):
    for fix in fixes:
        obj = fix['obj']
        if not obj.triggered and obj.floating:
            obj.floating = False
            obj.status = status


def get_fixes():
    fixes = []
    module = sys.modules[__name__]
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and hasattr(obj, '__name__') and hasattr(obj, '__module__'):
            fname = str(obj)
            if 'Fix' in fname and 'wrapper' in fname:
                fixes.append({'func': obj, 'obj': obj.__closure__[1].cell_contents, 'name':obj.__closure__[0].cell_contents.__name__})
    return fixes


def new_process(location, command):
    return subprocess.Popen(command, shell=True, cwd=location, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def print_table(fix_list):
    max_width = max(len(str(row['name'])) for row in fix_list)
    print(f"| {'TEST':<{max_width}} |  STATUS  | IMPORTANT")
    print(f"|{'-' * (max_width + 2)}|----------|------------")
    for row in fix_list:
        print(f"| {str(row['name']):<{max_width}} | {row['obj'].status:>8} | {row['obj'].message()}")


def info_table(fix_list):
    max_width_1 = max(len(str(row['name'])) for row in fix_list)
    max_width_2 = max(len(str(row['obj'].command)) for row in fix_list)
    print(f"| {'TEST':<{max_width_1}} | {'COMMAND':<{max_width_2}} | INFORMATION ")
    print(f"|{'-' * (max_width_1 + 2)}|{'-' * (max_width_2 + 2)}|------------")
    for row in fix_list:
        info = row['obj'].kwargs['info'] if 'info' in row['obj'].kwargs else ''
        print(f"| {str(row['name']):<{max_width_1}} | {row['obj'].command:>{max_width_2}} | {info:>6}")


def update(this_file, url):
    print(f"Updating from {url}...")
    new_file, headers = urllib.request.urlretrieve(url)
    os.chmod(new_file, 0o777)
    os.replace(new_file, this_file)
    print(f'Updated complete!')
    time.sleep(5)


def try_and_resolve(fixes, location, command):
    pass#TODO


def main():
    fix_list = get_fixes()
    opts, args = getopt.getopt(sys.argv, 'hulp:f:r:o:d:', ['help', 'doc'])
    path = DEFAULT_PATH
    command = DEFAULT_COMMAND
    customized_run = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(f'"{sys.argv[0]} -r <path>" the command to run. default is "{DEFAULT_COMMAND}"')
            print(f'"{sys.argv[0]} -p <path>" the path where the command takes place. default is "{DEFAULT_PATH}"')
            print(f'"{sys.argv[0]} -u" update from {UPDATE_URL}')
            print(f'"{sys.argv[0]} -l" list all fixes and some information about them')
            print(f'"{sys.argv[0]} -d <name>" show documentation for a specific fix')
            print(f'"{sys.argv[0]} -f <name>" run a specific fix (separate more than one with comma)')
            print(f'"{sys.argv[0]} -o <name>" omit a specific fix (separate more than one with comma)')
            print(f'"{sys.argv[0]} --doc" show documentation about this script')
        elif opt == '-l':
            info_table(fix_list)
            exit()
        elif opt == '-u':
            update(__file__, UPDATE_URL)
            exit()
        elif opt == '-p':
            if arg.endswith('/'):
                path = arg[0:-1]
            else:
                path = arg
        elif opt == '-f':
            arg_list = arg.split(",") if ',' in arg else [arg]
            fix_list = [fix for fix in fix_list if fix['name'] in arg_list]
            customized_run = True
        elif opt == '-o':
            arg_list = arg.split(",") if ',' in arg else [arg]
            fix_list = [fix for fix in fix_list if fix['name'] not in arg_list]
            customized_run = True
        elif opt == '-d':
            for fix in fix_list:
                if arg == fix['name']:
                    print(fix['name'])
                    print("-"*len(fix['name']))
                    print(fix['func'].__doc__)
            exit()
        elif opt == '-r':
            command = arg
            customized_run = True
        elif opt == '--doc':
            print(__main__.__doc__)
    fix_list = [fix for fix in fix_list if fix['obj'].command in (command, '')]
    if customized_run:
        info_table(fix_list)
        print(f'Running these tests with "{command}" in 5 seconds...')
        time.sleep(5)
    handler(fix_list, path, command)
    print_table(fix_list)


if __name__ == '__main__':
    main()
