import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from .utils import create_task
import re


ERROR_RE =  re.compile(r"! (.+?)\nl\.(\d+) (.+?)\n")
ERROR_RE2 =  re.compile(r"! (.+?)\n.+?\n.+?\nl\.(\d+) (.*?)\n")
WARNING_RE = re.compile(r"LaTeX Warning: (.*?)(?:on input line (\d+))?\.\n")

class LogFileError(Exception):
    pass


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/logviewer.ui')
class LogViewer(Gtk.Widget):
    __gtype_name__ = 'LogViewer'
    __gsignals__ = {
        'scroll-to': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
    }

    stack = Gtk.Template.Child()
    listbox = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self.file = None
        self.listbox.connect("row-activated", self.on_row_activated)

    def on_row_activated(self, box, row):
        self.emit("scroll-to", row.line_number)

    def set_path(self, path):
        self.file = Gio.File.new_for_path(path)
        if self.file.query_exists():
            create_task(self.parse_latex_log())
        else:
            self.stack.set_visible_child_name("empty")

    async def parse_latex_log(self):
        self.listbox.remove_all()
        success, contents, etag = await self.file.load_contents_async(None)
        if not success:
            self.stack.set_visible_child_name("empty")
            raise LogFileError(f"Error opening {file.peek_path()}")

        try:
            log_text = contents.decode("utf-8")
        except UnicodeError as err:
            self.stack.set_visible_child_name("empty")
            raise LogFileError(f"The file {file.peek_path()} is not encoded in unicode")

        errors = []
        warnings = []
        errors.extend(ERROR_RE.findall(log_text))
        errors.extend(ERROR_RE2.findall(log_text))
        warnings.extend(WARNING_RE.findall(log_text))
        for e in errors:
            row = Adw.ActionRow.new()
            row.add_css_class("error")
            row.set_title(e[0] + " at line " + e[1])
            row.set_subtitle(e[2])
            self.listbox.append(row)
            if e[1]:
                row.line_number = int(e[1])
                row.set_activatable(True)
                icon = Gtk.Image.new_from_icon_name("error-correct-symbolic")
                row.add_suffix(icon)
            else:
                row.set_activatable(False)
        for w in warnings:
            row = Adw.ActionRow.new()
            row.add_css_class("warning")
            row.set_title(w[0])
            if w[1]:
                row.line_number = int(w[1])
                row.set_activatable(True)
                icon = Gtk.Image.new_from_icon_name("error-correct-symbolic")
                row.add_suffix(icon)
            else:
                row.set_activatable(False)
            self.listbox.append(row)

        self.stack.set_visible_child_name("content")
