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
import asyncio

GtkSource.init()

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    start_pane = Gtk.Template.Child() # holds the editor
    end_pane = Gtk.Template.Child() # holds the pdf viewer
    start_pane_title = Gtk.Template.Child()
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

        buffer = self.source_view.get_buffer()
        buffer.connect("modified-changed", self.on_buffer_modified_changed)

    def get_file_info(self):
        if self._file is None:
            display_name = "New file"
            directory = "unsaved"
        else:
            info = self._file.query_info("standard::display-name",
                                         Gio.FileQueryInfoFlags.NONE)
            if info:
                display_name = info.get_attribute_string("standard::display-name")
            else:
                display_name = self._file.get_basename()

            directory = self._file.get_parent().peek_path()

        return directory, display_name

    def on_buffer_modified_changed(self, buffer):
        directory, display_name = self.get_file_info()
        if buffer.get_modified():
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

    def on_compile_action(self, action, param):
        create_task(self.compile())

    async def compile(self):
        await self.save()

        if self._file is None:
            toast = Adw.Toast.new("Compilation failed: file saving dismissed by user")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            return
        filename = self._file.peek_path()
        folder = self._file.get_parent().peek_path()

        interpreter = 'latexmk'
        cmd = [interpreter, '-synctex=1', '-interaction=nonstopmode', '-pdf',
               "-g", "--output-directory=" + folder, filename]

        success, log_text = await run_command_on_host(cmd)

        if not success:
            toast = Adw.Toast.new("Compilation failed")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            print(log_text)
            self.pdf_viewer.show_empty()
        else:
            toast = Adw.Toast.new("Compilation finished")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
            print(log_text)
            self.pdf_viewer.reload()

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
        buffer.set_modified(False)

        path = file.peek_path()
        path = path[:-4] + ".pdf"
        self.pdf_viewer.set_path(path)

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

        buffer = self.source_view.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)

        _, display_name = self.get_file_info()

        self._monitor.handler_block_by_func(self.file_monitor_cb)
        try:
            file = open(self._file.peek_path(), "w")
        except PermissionError:
            toast = Adw.Toast.new("Cannot save to {display_name}: permission denied")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)

        try:
            file.write(text)
        except (IOError, OSError):
            toast = Adw.Toast.new("Cannot save to {display_name}: can't write file")
            toast.set_timeout(2)
            self.toast_overlay.add_toast(toast)
        else:
            buffer.set_modified(False)
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

