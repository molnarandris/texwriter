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
import re

from gi.repository import GObject, Gio, GLib, Gtk


class LatexFileDialog(Gtk.FileDialog):
    def __init__(self):
        super().__init__()

        latex_filter = Gio.ListStore.new(Gtk.FileFilter)

        f = Gtk.FileFilter()
        f.add_mime_type("text/x-tex")
        latex_filter.append(f)

        f = Gtk.FileFilter()
        f.add_mime_type("text/plain")
        latex_filter.append(f)

        f = Gtk.FileFilter()
        f.add_pattern("*")
        f.set_name("All files")
        latex_filter.append(f)

        self.set_filters(latex_filter)
        self.set_modal(True)


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
        self._monitor = None
        self._display_name = 'Unsaved File'
        self.errors = [] #TODO: move to LatexProject
        self.warnings = []

    @property
    def exists(self):
        if self._file is None:
            return False
        return self._file.query_exists()

    @property
    def file(self):
        if self._file is None:
            raise LatexFileError("File does not exist")
        return self._file

    @file.setter
    def file(self, file):
        if self._monitor is not None:
            self._monitor.disconnect_by_func(self.on_file_change)
        if file is not None and file.query_exists():
            self._monitor = file.monitor(Gio.FileMonitorFlags.NONE, None)
            self._monitor.connect("changed", self.on_file_change)

            info_str = "standard::display-name"
            info = file.query_info(info_str, Gio.FileQueryInfoFlags.NONE)
            if info:
                self.display_name = info.get_attribute_string(info_str)
            else:
                self.display_name = self._file.get_basename()
        else:
            self.display_name = "Unsaved File"
        self._file = file

    @property
    def pwd_path(self):
        return self.file.get_parent().peek_path()

    @property
    def path(self):
        return self.file.peek_path()

    @GObject.Property(type=str)
    def display_name(self):
        return self._display_name

    @display_name.setter
    def display_name(self, display_name):
        self._display_name = display_name

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
        interpreter = 'latexmk'
        cmd = ['flatpak-spawn', '--host', interpreter, '-synctex=1',
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
            log_text = stdout.decode()
            self.parse_latex_log(log_text)

        if process.returncode == 0:
            print("Compile succeeded")
        else:
            msg = f"Compilation of {self.display_name} failed"
            if stderr:
                err_msg = stderr.decode()
                if err_msg.startswith("Portal call failed:"):
                    msg = msg + f": {interpreter} is not installed"
            raise LatexCompileError(msg)

    async def replace_contents(self, text):
        self._monitor.handler_block_by_func(self.on_file_change)
        try:
            with open(self.path, "w") as f:
                f.write(text)
            await asyncio.sleep(0.1)
        except PermissionError:
            raise LatexFileError(f"Permission denied: {self.path}")
        finally:
            self._monitor.handler_unblock_by_func(self.on_file_change)

    def parse_latex_log(self, log_text):

        error_pattern = re.compile(r"! (.+?)\nl\.(\d+) (.+?)\n")
        warning_pattern = re.compile(r"LaTeX Warning: (.*?)(?:on input line (\d+))?\.\n")

        self.errors = []
        for error in error_pattern.findall(log_text):
            e = LatexLogRow()
            e.type = "Error"
            e.line = int(error[1])
            e.title = error[0] + ": " + error[2]
            e.text_before = error[2]
            self.errors.append(e)

        self.warnings = []
        for warning in warning_pattern.findall(log_text):
            e = LatexLogRow()
            e.type = "Warning"
            e.title = warning[0]
            if warning[1]:
                e.line = int(warning[1])
            self.errors.append(e)


class LatexLogRow:
    def __init__(self):
        self.type = ""
        self.line = 0
        self.title = ""
        self.text_before = ""
        self.text_after = ""
