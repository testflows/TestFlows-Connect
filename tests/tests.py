#!/usr/bin/env python3
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
from testflows.core import main, test
from testflows.core import Test as TestBase

class TestShell(TestBase):
    description = """
    Suite of Shell tests.
    """
    def run(self):
        with test("import"):
            from testflows.connect import Shell

        with test("open"):
            with Shell() as bash:
                pass

        with test("execute command"):
            with Shell() as bash:
                bash("ls -la")

        with test("execute multiple commands"):
            with Shell() as bash:
                bash("echo Hello World")
                bash("ls -la")
                bash("echo Bye World")

        with test("share the same shell between different tests"):
            with Shell() as bash:
                with test("first test"):
                    bash("echo Hello World")
                with test("second test"):
                    bash("ls -la")
                with test("third test"):
                    bash("echo Bye World")

class Test(TestBase):
    def run(self):
        with test("import testflows.connect"):
            import testflows.connect

        with TestShell("suite Shell"):
            pass

if main():
    with Test("regression"):
        pass
