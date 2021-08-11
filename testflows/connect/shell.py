# Copyright 2019 Katteli Inc.
# TestFlows.com Open-Source Software Testing Framework (http://testflows.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import sys
import time

from contextlib import contextmanager
from collections import namedtuple

from testflows.core import current
from testflows.uexpect import spawn, ExpectTimeoutError

__all__ = ["Shell", "Parser"]

class Application(object):
    """Base class for all CLI applications
    launched and controlled using uExpect.
    """
    pass


class Parser(object):
    def __init__(self, pattern, types=None):
        if types is None:
            types = {}

        self.pattern = re.compile(pattern)
        self.types = types
        self.default = dict(self.pattern.groupindex)

        for k in self.default:
            self.default[k] = None

        self._match = None

    def parse(self, s):
        values = self.default
        self._match = self.pattern.match(s)

        if self._match:
            values = self._match.groupdict()
            for k, v in values.items():
                values[k] = self.types.get(k, str)(v)

        return values


class Command(object):
    def __init__(self, app, command, timeout=None, total=None, parser=None, name=None):
        self.app = app
        self.output = None
        self.exitcode = None
        self.command = command
        self.timeout = timeout
        self.total = total
        self.parser = parser
        self.values = None
        self.name = self.app.name
        if name:
            self.name = f"{self.app.name}.{name}"
        self.app.child.logger(self.app.test.message_io(self.name))
        self.execute()

    def get_exitcode(self):
        if getattr(self.app.commands, "get_exitcode", None) is None:
            return None

        while True:
            if not self.app.child.expect(self.app.prompt, timeout=0.001, expect_timeout=True):
                break
 
        command = self.app.commands.get_exitcode
        
        self.app.child.send(command, eol="")
        self.app.child.expect(re.escape(command))
        self.app.child.send("\r", eol="")
        self.app.child.expect("\n")
        self.app.child.expect(self.app.prompt)
        
        return int(self.app.child.before.rstrip().replace("\r", ""))

    def execute(self):
        self.app._send_command(self.command)

        next_timeout = self.timeout
        if next_timeout is None:
            next_timeout = sys.maxsize

        start_time = time.time()
        pattern = f"({self.app.prompt})|(\n)"

        while True:
            raised_timeout = False
            
            try:
                match = self.app.child.expect(pattern, timeout=next_timeout)

                if not self.output:
                    self.output = ""

                if match.groups()[0]:
                    self.output += self.app.child.before
                    break

                elif match.groups()[1]:
                    self.output += self.app.child.before + self.app.child.after

                    elapsed = time.time() - start_time

                    if self.total:
                        if elapsed >= self.total:
                            raised_timeout = True
                            raise ExpectTimeoutError(match.re, self.total, self.output)
                        next_timeout = max(self.timeout, self.total - elapsed)
                        continue
            
            except ExpectTimeoutError:
                if not raised_timeout:
                    self.output = self.app.child.before \
                        if self.output is None \
                        else (self.output + (self.app.child.before or ''))
                elapsed = time.time() - start_time

                if self.total:
                    if elapsed >= self.total:
                        raise
                    next_timeout = max(self.timeout, self.total - elapsed)
                    continue
                raise

        if self.output:
            self.output = self.output.rstrip().replace("\r", "")

        if self.parser:
            self.values = self.parser.parse(self.output)

        self.exitcode = self.get_exitcode()
        self.app.child.send("\r", eol="")
        self.app.child.expect("\n")

        return self

class AsyncCommand(Command):
    """Asynchronous command.
    """
    def __init__(self, app, command, timeout=None, parser=None, name=None):
        if timeout is None:
            timeout = 0.5

        if name is None:
            name = command

        super(AsyncCommand, self).__init__(app=app, command=command, timeout=timeout, total=None, parser=parser, name=name)

    def execute(self):
        self.app._send_command(self.command)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()
        self.app.child.logger(self.app.test.message_io(self.app.name))

    def close(self, ctrl="\03", test=None):
        """Abort async command"""
        if self.exitcode is not None:
            return

        self.app.send("\r", eol="")
        output = self.readlines()

        if self.exitcode is None:
            self.app.child.send(ctrl, eol="")
            output += self.readlines()

        return output

    def readlines(self, timeout=None, test=None):
        """Return currently available output.
        """
        if test is None:
            test = current()

        if timeout is None:
            timeout = self.timeout

        if self.app.test is not test:
            self.app.test = test
            self.app.child.logger(self.app.test.message_io(self.name))

        output = ""
        pattern = f"({self.app.prompt})|(\n)"

        while True:
            raised_timeout = False

            try:
                match = self.app.child.expect(pattern, timeout=timeout)
                # prompt
                if match.groups()[0]:
                    output += self.app.child.before
                    self.exitcode = self.get_exitcode()
                    self.app.child.send("\r", eol="")
                    self.app.child.expect("\n")
                    break
                # new line
                elif match.groups()[1]:
                    output += self.app.child.before + self.app.child.after

            except ExpectTimeoutError:
                output = self.app.child.before \
                    if output is None \
                    else (output + (self.app.child.before or ''))
                break

        output = output.rstrip().replace("\r", "")

        if output and self.parser:
            self.values = self.parser.parse(output)

        if self.output is None:
            self.output = ""

        self.output += output
        return output

ShellCommands = namedtuple("ShellCommands", "change_prompt get_exitcode")

class Shell(Application):
    """Connection to shell application.

    :param command: command to launch shell, default: ["/bin/bash", "--noediting"]
    :param prompt: prompt, default: r'[#\$] '
    :param change_prompt: command to change promptm default: None
    :param new_prompt: new prompt to set, default: None
    """
    name = "bash"
    prompt = r'[#\$] '
    new_prompt = "bash# "
    command = ["/bin/bash", "--noediting"]
    commands = ShellCommands(
        change_prompt="export PS1=\"{}\"",
        get_exitcode="echo $?"
        )
    timeout = 10
    multiline_prompt = ">"

    def __init__(self, command=None, prompt=None, new_prompt=None, name=None, spawn=spawn):
        self.command = command or self.command
        self.prompt = prompt or self.prompt
        self.new_prompt = new_prompt or self.new_prompt
        self.child = None
        self.test = None
        self.spawn = spawn
        self.name = name if name is not None else self.name

    def __enter__(self):
        return self

    def open(self, timeout=None, test=None):
        if timeout is None:
            timeout = self.timeout
        self.child = self.spawn(self.command)
        self.child.timeout(timeout)
        self.child.eol("\r")

        if test is None:
            test = current()

        if self.test is not test:
            self.test = test
            self.child.logger(self.test.message_io(self.name))

        if self.new_prompt and getattr(self.commands, "change_prompt", None):
            self.child.expect(self.prompt)
            
            change_prompt_command = self.commands.change_prompt.format(self.new_prompt)
            
            self.child.send(change_prompt_command)
            self.child.expect(re.escape(change_prompt_command))
            self.child.expect("\n")
            
            self.prompt = self.new_prompt

    def close(self):
        if self.child:
            child = self.child
            self.child = None
            child.close()

    def send(self, *args, **kwargs):
        command = kwargs.pop("command", None)

        if self.child is None:
            self.open()

        if command is not None:
            test = kwargs.pop("test", None)
            if test is None:
                test = current()

            if self.test is not test:
                self.test = test
                self.child.logger(self.test.message_io(self.name))

            return self._send_command(*args, **kwargs)

        return self.child.send(*args, **kwargs)

    def expect(self, *args, **kwargs):
        test = kwargs.pop("test", None)

        if test is None:
            test = current()

        if self.child is None:
            self.open()

        if self.test is not test:
            self.test = test
            self.child.logger(self.test.message_io(self.name))

        return self.child.expect(*args, **kwargs)

    def _send_command(self, command, timeout=60):
        """Send command.
        """
        self.child.expect(self.prompt)

        while True:
            if not self.child.expect(self.prompt, timeout=0.001, expect_timeout=True):
                break

        lines = command.strip().split("\n")

        for i, line in enumerate(lines):
            if i > 0:
                self.child.send("\n", eol="")
                self.child.expect("\n")
                self.child.expect(self.multiline_prompt, timeout=self.timeout, expect_timeout=False)

            if line:
                self.child.send(line, eol="")

        while True:
            if not self.child.expect("\n", timeout=0.001, expect_timeout=True):
                break

        self.child.send("\r", eol="")
        self.child.expect("\n", timeout=timeout)

    def __call__(self, command, timeout=None, total=None, parser=None, asynchronous=False,
            asyncronous=False, test=None, name=None):
        """Execute shell command.

        :param command: command to execute
        :param timeout: time to wait for the next line of output
        :param total: time to wait for the command to complete
            and return to the prompt, default: None (no limit)
        :param parser: output parser
        :param asynchronous: asynchronous command, default: None (not async)
        :param test: caller test
        """
        if test is None:
            test = current()

        if timeout is None:
            timeout = self.timeout

        if self.child is None:
            self.open(timeout)

        if self.test is not test:
            self.test = test

        if asyncronous or asynchronous:
            return AsyncCommand(self, command=command, timeout=None, parser=parser, name=name)

        return Command(self, command=command, timeout=timeout, total=total, parser=parser, name=name)

    def __exit__(self, type, value, traceback):
        self.close()

    @contextmanager
    def subshell(self, command, name="sub-bash", prompt=None):
        """Open subshell in the current shell.
        """
        def spawn(command):
            self.expect(self.prompt)
            self.send(command)
            return self.child

        def close():
            pass

        if self.child is None:
            self.open()

        child_close = self.child.close
        child_timeout = self.child.timeout
        child_eol = self.child.eol

        try:
            self.child.close = close

            with Shell(spawn=spawn, command=command, name=name, prompt=prompt) as sub_shell:
                try:
                    yield sub_shell
                finally:
                    sub_shell.send("exit")
                    sub_shell.expect("exit")
                    sub_shell.expect(self.prompt)
                    sub_shell.send("")
                    sub_shell.expect("\n")
        finally:
            self.child.close = child_close
            self.child.timeout = child_timeout
            self.child.eol = child_eol

