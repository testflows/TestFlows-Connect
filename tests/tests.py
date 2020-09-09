#!/usr/bin/env python3
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
import textwrap

from testflows.core import *
from testflows.asserts import error, values

@TestSuite
def suite(self):
    """Suite of Shell tests.
    """
    with Given("import"):
        from testflows.connect import Shell

    with Test("open"):
        with Shell() as bash:
            pass

    with Test("execute command"):
        with Shell() as bash:
            bash("ls -la")

    with Test("custom shell name"):
        with Shell(name="shell") as shell:
            shell("ls -la")

    with Test("execute command with custom name"):
        with Shell() as bash:
            bash("ls -la", name="ls")

    with Test("execute multiple commands"):
        with Shell() as bash:
            bash("echo Hello World")
            bash("ls -la")
            bash("echo Bye World")

    with Test("execute command with utf-8"):
        with Shell() as bash:
            bash("echo Gãńdåłf_Thê_Gręât")

    with Test("share the same shell between different tests"):
        with Shell() as bash:
            with Step("first test"):
                bash("echo Hello World")
            with Step("second test"):
                bash("ls -la")
            with Step("third test"):
                bash("echo Bye World")

    with Test("check command output"):
        with Shell() as bash:
            with Step("one line output"):
                assert bash("echo Hello World").output == "Hello World", error()
            with Step("empty output"):
                assert bash("echo ").output == "", error()
            with Step("multi line output"):
                text = "line1\\nline2"
                with values() as that:
                    assert that(bash(f"echo -e \"{text}\"").output) == text.replace("\\n", "\n"), error()

    with Test("check command exitcode"):
        with Shell() as bash:
            with Step("exit code 0"):
                assert bash("ls -la").exitcode == 0, error()
            with Step("exit code 2"):
                assert bash("ls /foo__").exitcode == 2, error()

    with Test("check timeout"):
        with Shell() as bash:
            bash.timeout = 6
            with Step("timeout 1 sec"):
                bash("echo hello; sleep 0.75; " * 5)

    with Test("async command"):
        with Shell() as bash:
            with bash("tail -f /proc/cpuinfo", asyncronous=True) as tail:
                tail.readlines()

    with Test("async command with custom name"):
        with Shell() as bash:
            with bash("tail -f /proc/cpuinfo", asyncronous=True, name="cpuinfo") as tail:
                tail.readlines()

    with Test("check double prompts before command"):
        with Shell() as bash:
            bash.send("")
            bash("ls")

    with Test("check double prompts after command"):
        with Shell() as bash:
            for i in range(100):
                bash.send("")
                bash("ls\r\n")
                bash("ls; echo -e 'bash# \nbash# '")

    with Test("check empty lines before command"):
        with Shell() as bash:
            for i in range(100):
                bash("\n\n\necho \"foo\"")

    with Test("check empty lines after command"):
        with Shell() as bash:
            for i in range(100):
                bash("echo \"foo\"\n\n\n")

    with Test("check empty lines before and after command"):
        with Shell() as bash:
            for i in range(100):
                bash("\n\n\necho \"foo\"\n\n\n")

    with Test("check multiline command"):
        with Shell() as bash:
            for i in range(100):
                bash("cat << HEREDOC > foo\nline 1\nline 2\nline 3\nHEREDOC")

    with Test("check multiline command with long lines"):
        with Shell() as bash:
            cmd = ("cat << HEREDOC > foo\n"
               "'111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111', '22222222222222222'\n"
               "'22222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222', '33333333333333333'\n"
               "HEREDOC")
            for i in range(100):
                bash(cmd)

    with Test("check multiline command using echo -e with long lines"):
        with Shell() as bash:
            cmd = textwrap.dedent("""
                echo -e "
                SELECT hex(
                    aes_decrypt_mysql(
                        'aes-256-cbc',
                        dictGet('default.dict_user_data', 'secret', toUInt64(1)),
                        '11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111', '22222222222222222$
                    )
                )
                "
                """)
            for i in range(100):
                bash(cmd)

@TestModule
def regression(self):
   with Test("import testflows.connect"):
       import testflows.connect

   Suite(run=suite)

if main():
    Module(run=regression)
