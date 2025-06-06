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
import asyncio

GtkSource.init()

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    editor = Gtk.Template.Child()
    pdf_viewer = Gtk.Template.Child()
    source_view = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    banner = Gtk.Template.Child()

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

        self._monitor = None
        self._file = None

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

    async def open(self, file=None):

        if file is None:

            dialog = Gtk.FileDialog()

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

            dialog.set_filters(latex_filter)

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

        if self._monitor is not None:
            self._monitor.disconnect_by_func(self.file_monitor_cb)
        self._monitor = file.monitor(Gio.FileMonitorFlags.NONE, None)
        self._monitor.connect("changed", self.file_monitor_cb)
        self._file = file

        buffer = self.source_view.get_buffer()
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

    def on_save_action(self, action, param):
        create_task(self.save())

    async def save(self):
        if self._file is None:
            dialog = Gtk.FileDialog()

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

            dialog.set_filters(latex_filter)

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

        else:
            file = self._file


        buffer = self.source_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)

        info = file.query_info("standard::display-name",
                               Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()

        self._monitor.handler_block_by_func(self.file_monitor_cb)
        try:
            file = open(file.peek_path(), "w")
        except PermissionError:
            toast = Adw.Toast.new("Cannot save to {display_name}: permission denied")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)

        try:
            file.write(text)
        finally:
            file.close()
            await asyncio.sleep(0.05) #need to wait a bit before unblocking
            self._monitor.handler_unblock_by_func(self.file_monitor_cb)

    def file_monitor_cb(self, monitor, file, other_file, event):
        if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            return
        self.banner.set_revealed(True)

    @Gtk.Template.Callback()
    def on_banner_button_clicked(self, user_data):
        self.banner.set_revealed(False)
        create_task(self.open(self._file))

