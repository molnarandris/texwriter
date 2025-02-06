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
gi.require_version("GtkSource", "5")

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GLib
from gi.repository import GtkSource

GtkSource.init()

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    open_button = Gtk.Template.Child()
    text_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.on_open)
        self.add_action(open_action)

    def on_open(self, action, _):
        dialog = Gtk.FileDialog()
        filter_text = Gtk.FileFilter()
        filter_text.add_mime_type("text/plain")
        filter_tex = Gtk.FileFilter()
        filter_tex.add_mime_type("text/x-tex")
        filter_all = Gtk.FileFilter()
        filter_all.add_pattern("*")
        filter_all.set_name("All files")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_tex)
        filters.append(filter_text)
        filters.append(filter_all)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_tex)
        dialog.open(self, None, self.on_open_response)

    def on_open_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error as err:
            cancelled = err.matches(Gtk.dialog_error_quark(),
                                    Gtk.DialogError.DISMISSED) or \
                        err.matches(Gtk.dialog_error_quark(),
                                    Gtk.DialogError.CANCELLED)
            if not cancelled:
                #FIXME: Display Error to user
                pass
        else:
            if file is not None:
                self.open_file(file)

    def open_file(self, file):
        source_file = GtkSource.File()
        source_file.set_location(file)
        buffer = self.text_view.props.buffer
        file_loader = GtkSource.FileLoader.new(buffer, source_file)
        file_loader.load_async(io_priority=GLib.PRIORITY_DEFAULT,
                               cancellable=None,
                               progress_callback=None,
                               callback=self.open_file_cb)

    def open_file_cb(self, file_loader, result, user_data):
        try:
            file_loader.load_finish(result)
        except GLib.Error as err:
            # Loader loads content even if there is an error...
            #FIXME: Notify user about the error
            pass
        else:
            buffer = self.text_view.props.buffer
            manager = GtkSource.LanguageManager.get_default()
            latex = manager.get_language("latex")
            buffer.set_language(latex)
