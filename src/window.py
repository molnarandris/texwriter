# window.py
#
# Copyright 2025 Andras Molnar
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
gi.require_version("GtkSource", "5")
from gi.repository import GtkSource
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GLib
from .utils import create_task, run_command_on_host
from .pdfviewer import PdfViewer
from .logviewer import LogViewer
from .editor import Editor
from .latexfile import LATEX_FILTER, LatexFileError, LatexFile
import re
import asyncio

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    start_pane = Gtk.Template.Child() # holds the editor
    end_pane = Gtk.Template.Child() # holds the pdf viewer
    start_pane_title = Gtk.Template.Child()
    pdf_viewer = Gtk.Template.Child()
    log_viewer = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    pdf_log_stack = Gtk.Template.Child()
    editor = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        action = Gio.SimpleAction(name="synctex")
        action.connect("activate", lambda *_ : create_task(self.synctex()))
        self.add_action(action)
        self.get_application().set_accels_for_action("win.synctex", ['F7'])

        action = Gio.SimpleAction(name="compile")
        action.connect("activate", lambda *_ : create_task(self.compile()))
        self.add_action(action)
        self.get_application().set_accels_for_action("win.compile", ['F5'])

        action = Gio.SimpleAction(name="open")
        action.connect("activate", lambda *_ : create_task(self.open()))
        self.add_action(action)
        self.get_application().set_accels_for_action("win.open", ['<Ctrl>o'])

        action = Gio.SimpleAction(name="save")
        action.connect("activate", self.on_save_action)
        self.add_action(action)
        self.get_application().set_accels_for_action("win.save", ['<Ctrl>s'])

        self._monitor = None
        self._file = LatexFile()
        self._file.connect("external-change", self.on_file_external_change)

        self.editor.connect("modified-changed", self.on_editor_modified_changed)


    def on_editor_modified_changed(self, editor, modified):
        directory, display_name = self._file.get_info()
        if modified:
            title = "• " + display_name
        else:
            title = display_name

        self.start_pane_title.set_title(title)
        self.start_pane_title.set_subtitle(directory)

    @Gtk.Template.Callback()
    def on_show_pdf_button_clicked(self, button):
        self.end_pane.set_visible(True)
        self.start_pane.set_visible(False)

    @Gtk.Template.Callback()
    def on_show_editor_button_clicked(self, button):
        self.end_pane.set_visible(False)
        self.start_pane.set_visible(True)

    async def synctex(self):
        line, column = self.editor.get_cursor_position()
        tex_path = self._file.get_path()
        if tex_path is None:
            return
        pos = str(line) + ":" + str(column) + ":" + tex_path
        pdf_path = tex_path[:-3] + "pdf"
        cmd = ['synctex', 'view', '-i', pos, '-o', pdf_path]

        success, output = await run_command_on_host(cmd)

        record = "Page:(.*)\n.*\n.*\nh:(.*)\nv:(.*)\nW:(.*)\nH:(.*)"
        rectangles = []
        for match in re.findall(record, output):
            page = int(match[0])-1
            x = float(match[1])
            y = float(match[2])
            width = float(match[3])
            height = float(match[4])
            rectangles.append((width, height, x, y, page))
        self.pdf_viewer.synctex_fwd(rectangles)

    async def compile(self):
        await self.save()

        if self._file is None:
            toast = Adw.Toast.new("Compilation failed: file saving dismissed by user")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            return
        filename = self._file.get_path()
        folder = self._file.get_dir()

        if filename is None:
            return

        interpreter = 'latexmk'
        cmd = [interpreter, '-synctex=1', '-interaction=nonstopmode', '-pdf',
               "-g", "--output-directory=" + folder, filename]

        success, log_text = await run_command_on_host(cmd)

        await self.log_viewer.parse_latex_log()

        if not success:
            toast = Adw.Toast.new("Compilation failed")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            self.pdf_viewer.show_empty()
            self.pdf_log_stack.set_visible_child_name("log")
        else:
            toast = Adw.Toast.new("Compilation finished")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            self.pdf_viewer.reload()
            await self.synctex()

    async def open(self, file=None):

        if file is None:

            dialog = Gtk.FileDialog()
            dialog.set_filters(LATEX_FILTER)

            try:
                file = await dialog.open(self, None)
            except GLib.GError as err:
                if err.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                    return
                if err.matches(Gtk.dialog_error_quark(), Gtk.DialogError.FAILED):
                    toast = Adw.Toast.new("Could not select file")
                    toast.set_timeout(2)
                    self.toast_overlay.add_toast(toast)
                    return
                raise

        try:
            text = await self._file.open_file(file)
        except LatexFileError as e:
            toast = Adw.Toast.new(str(e))
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            return

        self.editor.set_text(text)

        path = file.peek_path()
        path = path[:-4] + ".pdf"
        self.pdf_viewer.set_path(path)
        path = path[:-4] + ".log"
        self.log_viewer.set_path(path)

    def on_save_action(self, action, param):
        create_task(self.save())

    async def save(self):
        if self._file.get_path() is None:
            dialog = Gtk.FileDialog()
            dialog.set_filters(LATEX_FILTER)

            try:
                file = await dialog.save(self, None)
            except GLib.GError as err:
                if err.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                    return
                if err.matches(Gtk.dialog_error_quark(), Gtk.DialogError.FAILED):
                    toast = Adw.Toast.new("Cannot save to file")
                    toast.set_timeout(2)
                    self.toast_overlay.add_toast(toast)
                    return
                raise

        text = self.editor.get_text()

        try:
            await self._file.save(text)
        except LatexFileError as e:
            toast = Adw.Toast.new(str(e))
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
        else:
            self.editor.set_modified(False)

    def on_file_external_change(self, latexfile):
        self.banner.set_revealed(True)

    @Gtk.Template.Callback()
    def on_switch_log_button_clicked(self, user_data):
        if self.pdf_log_stack.get_visible_child_name() == "pdf":
            self.pdf_log_stack.set_visible_child_name("log")
        else:
            self.pdf_log_stack.set_visible_child_name("pdf")
