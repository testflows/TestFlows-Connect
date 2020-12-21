# Copyright 2020 Katteli Inc.
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
from contextlib import contextmanager

from .shell import Shell

__all__ = ["SSH"]

@contextmanager
def SSH(host, username, password=None, command="{client} {username}@{host} {options}",
        client="ssh", options=["-v"], port=None, prompt=r"[\$#] ", new_prompt="bash# "):
    """Open SSH terminal to a remote host.
    """
    if options is None:
        options = []

    if port is not None:
        options.append(f"-p {port}")

    with Shell(name=f"ssh-{host}") as bash:
        command = command.format(client=client, username=username, host=host, options=" ".join(options).strip())

        bash.send(command)

        c = bash.expect(r"(Last login)|(Could not resolve hostname)|(Connection refused)|"
            r"(Are you sure you want to continue connecting)")

        if c.group() == "Are you sure you want to continue connecting":
            bash.send("yes", delay=0.5)
            c = bash.expect(r"(Last login)")

        if c.group() == "Last login":
            bash.expect(prompt)
        else:
            raise IOError(c.group())

        bash.send("\r")

        def spawn(command):
            bash.send(" ".join(command))
            return bash.child

        def close():
            bash.send("exit")

        child_close = bash.child.close
        child_timeout = bash.child.timeout
        child_eol = bash.child.eol

        try:
            bash.child.close = close

            with Shell(spawn=spawn, name=host, prompt=prompt, command=[""], new_prompt=new_prompt) as ssh:
                yield ssh
        finally:
            bash.child.close = child_close
            bash.child.timeout = child_timeout
            bash.child.eol = child_eol
