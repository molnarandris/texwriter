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
from .asyncio import create_task

GtkSource.init()

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    editor = Gtk.Template.Child()
    pdf_viewer = Gtk.Template.Child()
    source_view = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        action = Gio.SimpleAction(name="compile")
        action.connect("activate", self.on_compile_action)
        self.add_action(action)
        self.get_application().set_accels_for_action("win.compile", ['F5'])

        action = Gio.SimpleAction(name="open")
        action.connect("activate", self.on_open_action)
        self.add_action(action)
        self.get_application().set_accels_for_action("win.open", ['<Ctrl>o'])

        action = Gio.SimpleAction(name="save")
        action.connect("activate", self.on_save_action)
        self.add_action(action)
        self.get_application().set_accels_for_action("win.save", ['<Ctrl>s'])

    @Gtk.Template.Callback()
    def on_show_pdf_button_clicked(self, button):
        self.pdf_viewer.set_visible(True)
        self.editor.set_visible(False)

    @Gtk.Template.Callback()
    def on_show_editor_button_clicked(self, button):
        self.pdf_viewer.set_visible(False)
        self.editor.set_visible(True)

    def on_compile_action(self, action, param):
        print("Compiling")

    def on_open_action(self, action, param):
        create_task(self.open())

    async def open(self):
        dialog = Gtk.FileDialog()
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

        success, contents, etag = await file.load_contents_async(None)
        if not success:
            toast = Adw.Toast.new(f"Error opening {file.peek_path()}")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            return

        try:
            text = contents.decode("utf-8")
        except UnicodeError as err:
            toast = Adw.Toast.new(f"The file {file.peek_path()} is not encoded in unicode")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            return

        buffer = self.source_view.get_buffer()
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

    def on_save_action(self, action, param):
        print("Saving")
