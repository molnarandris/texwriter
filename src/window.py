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
import asyncio, re
gi.require_version("GtkSource", "5")

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GLib
from gi.repository import GtkSource
from gi.repository import GObject

from .latexfile import LatexFileDialog, LatexFile, LatexFileError, LatexCompileError, InterpreterMissingError
from .pdfviewer import PdfViewer
from .logviewer import LogViewer

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
    logviewer = Gtk.Template.Child()
    result_stack = Gtk.Template.Child()

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

        action = Gio.SimpleAction(name="synctex")
        action.connect("activate", self.on_synctex_action)
        self.add_action(action)

        buffer = self.text_view.get_buffer()
        buffer.connect("modified-changed", self.on_buffer_modified_changed)
        manager = GtkSource.LanguageManager.get_default()
        latex = manager.get_language("latex")
        buffer.set_language(latex)

        self.latexfile = LatexFile()
        self._compile_task = None
        self._old_compile_task = None

        self.latexfile.connect("modified", self.on_file_modified)
        self.logviewer.connect("scroll-to", self.scroll_to)
        self.banner.connect("button-clicked", self.on_banner_button_clicked)

        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        self.latexfile.bind_property("display-name", self.title, "label",
                                     GObject.BindingFlags.SYNC_CREATE)

        keybuffer = GtkSource.Buffer()
        keybuffer.set_text("\\alpha \\beta \\gamma")
        provider = GtkSource.CompletionWords.new("main")
        provider.register(keybuffer)
        provider.props.minimum_word_size = 2
        completion = self.text_view.get_completion()
        completion.props.select_on_show = True
        completion.add_provider(provider)

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
        if self._compile_task and not self._compile_task.done():
            self._old_compile_task = self._compile_task

        self._compile_task = asyncio.create_task(self.compile())

    async def compile(self, old_task = None):
        if self._old_compile_task and not self._old_compile_task.done():
            self._old_compile_task.cancel()
            try:
                await self._old_compile_task
            except asyncio.CancelledError:
                pass
        self.compile_button_stack.set_visible_child_name("cancel")

        if not self.latexfile.exists:
            await self.save(None)

        buffer = self.text_view.props.buffer
        if buffer.get_modified():
            await self.save(self.latexfile.file)

        try:
            success, log_text = await self.latexfile.compile()
        except InterpreterMissingError as err:
            msg = f"Compilation failed: {interpreter} is missing"
            toast = Adw.Toast(title=msg, timeout=2)
            self.overlay.add_toast(toast)
        except LatexFileError as err:
            print("Error at compilation:", err)
        else:
            self.logviewer.set_content(log_text)
            if success:
                self.pdfviewer.set_file(self.latexfile.path[:-3] + "pdf")
                self.result_stack.set_visible_child_name("pdf")
            else:
                msg = "Compilation failed"
                toast = Adw.Toast(title=msg, timeout=2)
                self.overlay.add_toast(toast)
                self.pdfviewer.set_file(None)
                self.result_stack.set_visible_child_name("log")
        finally:
            # If there is still a compilation running, don't reset state
            if self._compile_task is asyncio.current_task():
                self.compile_button_stack.set_visible_child_name("compile")
                self._compile_task = None

    def on_compile_cancel_action(self, action, _):
        if self._compile_task and not self._compile_task.done():
            self._compile_task.cancel()

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

    def scroll_to(self, _, line, text_before, text_after):
        buffer = self.text_view.props.buffer
        _, it = buffer.get_iter_at_line(line-1)
        bound = it.copy()
        bound.forward_to_line_end()

        if line == 0:
            return

        match_start, match_end = it.forward_search(text_before, Gtk.TextSearchFlags.TEXT_ONLY, bound)

        #buffer.apply_tag_by_name('highlight', *result)
        #GLib.timeout_add(500, lambda: buffer.remove_tag_by_name('highlight',*result))
        #it = result[0]
        self.text_view.scroll_to_iter(match_end, 0.3, False, 0, 0)
        buffer.place_cursor(match_end)
        self.text_view.grab_focus()

    def on_synctex_action(self, action, _):
        asyncio.create_task(self.synctex_fwd())

    async def synctex_fwd(self):
        buffer = self.text_view.get_buffer()
        it = buffer.get_iter_at_mark(buffer.get_insert())
        line = it.get_line()
        column = it.get_line_offset()
        tex_path = self.latexfile.path
        pos = str(line) + ":" + str(column) + ":" + tex_path
        pdf_path = self.latexfile.path[:-3] + "pdf"
        cmd = ['flatpak-spawn', '--host', 'synctex',
               'view', '-i', pos, '-o', pdf_path]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.terminate()
            raise
        else:
            record = "Page:(.*)\n.*\n.*\nh:(.*)\nv:(.*)\nW:(.*)\nH:(.*)"
            rectangles = []
            for match in re.findall(record, stdout.decode()):
                page = int(match[0])-1
                x = float(match[1])
                y = float(match[2])
                width = float(match[3])
                height = float(match[4])
                rectangles.append((width, height, x, y, page))
            for r in rectangles:
                print(r)
