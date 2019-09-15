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

from testflows.core import current_test
from testflows.uexpect import spawn

__all__ = ["Shell"]

class Application(object):
    """Base class for all CLI applications
    launched and controlled using uexpect.
    """
    pass


class Command(object):
    def __init__(self, app, command, timeout=None):
        self.app = app
        self.output = None
        self.exitcode = None
        self.command = command
        self.timeout = timeout
        self.execute()

    def execute(self):
        self.app.child.expect(self.app.prompt)
        self.app.child.send(self.command, eol="\r")
        self.app.child.expect(re.escape(self.command))
        self.app.child.expect(self.app.prompt, timeout=self.timeout)
        self.app.child.send("\r", eol="")
        self.app.child.expect("\n")
        return self


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
    change_prompt = "export PS1={}"
    timeout = 10

    def __init__(self, command=None, prompt=None, change_prompt=None, new_prompt=None):
        self.command = command or self.command
        self.prompt = prompt or self.prompt
        self.change_prompt = change_prompt or self.change_prompt
        self.new_prompt = new_prompt
        self.child = None
        self.test = None

    def __enter__(self):
        return self

    def open(self):
        self.child = spawn(self.command)
        self.child.timeout(self.timeout)
        self.child.eol("\r")

    def close(self):
        if self.child:
            self.child.close()

    def __call__(self, command, timeout=None, test=None):
        """Execute shell command.

        :param command: command to execute
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

        return Command(self, command=command, timeout=timeout)

    def __exit__(self, type, value, traceback):
        self.close()
