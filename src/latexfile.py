# window.py
#
# Copyright 2025 András Molnár
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import gi
import asyncio

from gi.repository import GObject, Gio, GLib

class LatexFileError(Exception):
    def __init__(self, message):
        self.message = message

class LatexCompileError(Exception):
    def __init__(self, message):
        self.message = message


class LatexFile(GObject.Object):
    __gtype_name__ = "LatexFile"

    __gsignals__ = {
        'modified': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._file = None
        self._file_monitor_id = None
        self._monitor = None

    @property
    def file(self):
        if self._file is None:
            raise LatexFileError("File does not exist")
        return self._file

    @file.setter
    def file(self, file):
        if self._file_monitor_id is not None and self._monitor is not None:
            self._monitor.disconnect(self._file_monitor_id)
        if file is not None:
            monitor = file.monitor(Gio.FileMonitorFlags.NONE, None)
            self._file_monitor_id = monitor.connect("changed",
                                                    self.on_file_change)
            self._monitor = monitor
        self._file = file

    @property
    def pwd_path(self):
        return self.file.get_parent().peek_path()

    @property
    def path(self):
        return self.file.peek_path()

    @property
    def display_name(self):
        file = self.file
        info = file.query_info("standard::display-name",
                               Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()
        return display_name

    def on_file_change(self, monitor, file, other_file, event):
        if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            return
        self.emit("modified")

    async def load_contents_async(self):
        path = self.file.peek_path()
        try:
            contents = await self.file.load_contents_async()
        except GLib.Error:
            raise LatexFileError(f"Can't open {path}: file loading error")

        if not contents[0]:
            raise LatexFileError(f"Can't open {path}: file reading error")

        try:
            text = contents[1].decode('utf-8')
        except UnicodeError:
            msg = f"Unable to open {path}: the file is not encoded with UTF-8"
            raise LatexFileError(msg)

        return text

    async def compile(self):
        """Run LaTeX asynchronously on self.file."""
        cmd = ['flatpak-spawn', '--host', 'latexmk', '-synctex=1',
               '-interaction=nonstopmode', '-pdf', "-g",
               "--output-directory=" + self.pwd_path,
               self.path]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if stdout:
            #print(f"Output:\n{stdout.decode()}")
            pass
        if stderr:
            #print(f"Errors:\n{stderr.decode()}")
            pass

        if process.returncode == 0:
            print("Compile succeeded")
        else:
            msg = f"Compilation of {self.display_name} failed"
            raise LatexCompileError(msg)

    async def replace_contents(self, text):
        with GObject.signal_handler_block(self._monitor,self._file_monitor_id):
            try:
                with open(self.path, "w") as f:
                    f.write(text)
                await asyncio.sleep(0.1)
            except PermissionError:
                raise LatexFileError(f"Permission denied: {self.path}")

