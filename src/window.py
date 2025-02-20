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
gi.require_version("GtkSource", "5")

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GLib
from gi.repository import GtkSource
from gi.repository import GObject

from .latexfile import LatexFileDialog, LatexFile, LatexFileError, LatexCompileError
from .pdfviewer import PdfViewer

GtkSource.init()

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    open_button = Gtk.Template.Child()
    compile_button_stack = Gtk.Template.Child()
    text_view = Gtk.Template.Child()
    banner = Gtk.Template.Child()
    overlay = Gtk.Template.Child()
    title = Gtk.Template.Child()
    subtitle = Gtk.Template.Child()
    paned = Gtk.Template.Child()
    pdfviewer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        action = Gio.SimpleAction(name="open")
        action.connect("activate", self.on_open)
        self.add_action(action)

        action = Gio.SimpleAction(name="compile")
        action.connect("activate", self.on_compile_action)
        self.add_action(action)

        action = Gio.SimpleAction(name="compile-cancel")
        action.connect("activate", self.on_compile_cancel_action)
        self.add_action(action)

        action = Gio.SimpleAction(name="save")
        action.connect("activate", self.on_save_action)
        self.add_action(action)

        action = Gio.SimpleAction(name="save-as")
        action.connect("activate", self.on_save_as_action)
        self.add_action(action)

        buffer = self.text_view.get_buffer()
        buffer.connect("modified-changed", self.on_buffer_modified_changed)
        manager = GtkSource.LanguageManager.get_default()
        latex = manager.get_language("latex")
        buffer.set_language(latex)

        self.latexfile = LatexFile()
        self._compile_task = None

        self.latexfile.connect("modified", self.on_file_modified)

        self.banner.connect("button-clicked", self.on_banner_button_clicked)

        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        self.latexfile.bind_property("display-name", self.title, "label",
                                     GObject.BindingFlags.SYNC_CREATE)

    def on_open(self, action, _):
        self.open_task = asyncio.create_task(self.open())

    async def open(self, file=None):
        if file is None:
            dialog = LatexFileDialog()

            try:
                file = await dialog.open(parent=self)
            except GLib.Error as err:
                quark = Gtk.dialog_error_quark()
                if err.matches(quark, Gtk.DialogError.FAILED):
                    msg = "Can't open file"
                    toast = Adw.Toast(title=msg, timeout=2)
                    self.overlay.add_toast(toast)
                return

        assert file is not None #I think dialog returns either error or file

        self.latexfile.file = file

        try:
            text = await self.latexfile.load_contents_async()
        except LatexFileError as err:
            # Loader loads content even if there is an error...
            toast = Adw.Toast(title=err.message, timeout=2)
            self.overlay.add_toast(toast)
            return

        buffer = self.text_view.props.buffer
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)
        buffer.set_modified(False)

        self.subtitle.set_label(self.latexfile.pwd_path)
        self.pdfviewer.set_file(self.latexfile.path[:-3] + "pdf")


    def on_buffer_modified_changed(self, buffer):
        if buffer.get_modified():
            title = "• " + self.latexfile.display_name
        else:
            title = self.latexfile.display_name
        self.title.set_label(title)

    def on_file_modified(self, latexfile):
        msg = "File has changed."
        lbl = "Reload"
        self.banner.set_title(msg)
        self.banner.set_button_label(lbl)
        self.banner.set_revealed(True)

    def on_banner_button_clicked(self, button):
        self.banner.set_revealed(False)
        asyncio.create_task(self.open(self.latexfile.file))

    def on_compile_action(self, action, _):
        if self._compile_task is not None:
            old_task = self._compile_task
        else:
            old_task = None
        self._compile_task = asyncio.create_task(self.compile(old_task))

    async def compile(self, old_task=None):
        if old_task is not None:
            old_task.cancel()
            await old_task
        self.compile_button_stack.set_visible_child_name("cancel")

        if not self.latexfile.exists:
            await self.save(None)

        buffer = self.text_view.props.buffer
        if buffer.get_modified():
            await self.save(self.latexfile.file)

        try:
            await self.latexfile.compile()
        except asyncio.CancelledError:
            print("Compilation canceled")
            raise
        except LatexCompileError as err:
            toast = Adw.Toast(title=err.message, timeout=2)
            self.overlay.add_toast(toast)
            self.pdfviewer.set_file(None)
        except LatexFileError as err:
            print(err)
        else:
            self.pdfviewer.set_file(self.latexfile.path[:-3] + "pdf")
        finally:
            self.compile_button_stack.set_visible_child_name("compile")

    def on_compile_cancel_action(self, action, _):
        if self._compile_task is not None:
            self._compile_task.cancel()
        self._compile_task = None

    def on_save_action(self, action, _):
        try:
            file = self.latexfile.file
        except LatexFileError:
            file = None
        self._save_task = asyncio.create_task(self.save(file))

    def on_save_as_action(self, action, _):
        self._save_task = asyncio.create_task(self.save(None))

    async def save(self, file):
        if file is None:
            dialog = LatexFileDialog()
            try:
                file = await dialog.save(parent=self)
            except GLib.Error as err:
                quark = Gtk.dialog_error_quark()
                if err.matches(quark, Gtk.DialogError.FAILED):
                    msg = "Can't save to file"
                    toast = Adw.Toast(title=msg, timeout=2)
                    self.overlay.add_toast(toast)
                return

            try:
                old_file = self.latexfile.file
            except LatexFileError:
                old_file = None
            self.latexfile.file = file

        buffer = self.text_view.props.buffer
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)

        try:
            await self.latexfile.replace_contents(text)
        except LatexFileError as err:
            toast = Adw.Toast(title=err.message, timeout=2)
            self.overlay.add_toast(toast)
            self.latexfile.file = old_file
        else:
            buffer.set_modified(False)

        try:
            self.subtitle.set_label(self.latexfile.pwd_path)
        except LatexFileError:
            self.subtitle.set_label("Unsaved")

