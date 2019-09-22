# Copyright 2019 Vitaliy Zakaznikov, TestFlows Test Framework (http://testflows.com)
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
import time

from collections import namedtuple

from testflows.core import current_test
from testflows.uexpect import spawn, ExpectTimeoutError

__all__ = ["Shell", "Parser"]

class Application(object):
    """Base class for all CLI applications
    launched and controlled using uexpect.
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
    def __init__(self, app, command, timeout=None, total=None, parser=None):
        self.app = app
        self.output = None
        self.exitcode = None
        self.command = command
        self.timeout = timeout
        self.total = total
        self.parser = parser
        self.values = None
        self.execute()

    def get_exitcode(self):
        self.app.child.send(self.app.commands.get_exitcode, eol="\r")
        self.app.child.expect("\n")
        self.app.child.expect(self.app.prompt)
        return int(self.app.child.before.rstrip().replace("\r", ""))

    def execute(self):
        self.app.child.expect(self.app.prompt)
        self.app.child.send(self.command, eol="\r")
        for i in range(self.command.count("\n") + 1):
            self.app.child.expect("\n")
        next_timeout = self.timeout
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
                    self.output = self.app.child.before if self.output is None else self.output + (self.app.child.before or '')
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
    command = ["/bin/bash", "--noediting"]
    commands = ShellCommands(
        change_prompt="export PS1=\"{}\"",
        get_exitcode="echo $?"
        )
    timeout = 10

    def __init__(self, command=None, prompt=None, new_prompt="bash# "):
        self.command = command or self.command
        self.prompt = prompt or self.prompt
        self.new_prompt = new_prompt
        self.child = None
        self.test = None

    def __enter__(self):
        return self

    def open(self):
        self.child = spawn(self.command)
        self.child.timeout(self.timeout)
        self.child.eol("\r")
        if self.new_prompt:
            self.child.expect(self.prompt)
            self.child.send(self.commands.change_prompt.format(self.new_prompt))
            self.child.expect("\n")
            self.prompt = self.new_prompt

    def close(self):
        if self.child:
            self.child.close()

    def __call__(self, command, timeout=None, total=None, parser=None, test=None):
        """Execute shell command.

        :param command: command to execute
        :param timeout: time to wait for the next line of output
        :param total: time to wait for the command to complete
            and return to the prompt, default: None (no limit)
        :param parser: output parser
        :param test: caller test
        """
        if test is None:
            test = current_test.object

        if timeout is None:
            timeout = self.timeout

        if self.child is None:
            self.open()

        if self.test is not test:
            self.test = test
            self.child.logger(self.test.message_io(self.name))

        return Command(self, command=command, timeout=timeout, total=total, parser=parser)

    def __exit__(self, type, value, traceback):
        self.close()
