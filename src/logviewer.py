import re
from gi.repository import Gtk, Adw, GObject

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/logviewer.ui')
class LogViewer(Gtk.Widget):
    __gtype_name__ = "LogViewer"
    __gsignals__ = {
        'scroll-to': (GObject.SIGNAL_RUN_FIRST, None, (int, str, str)),
    }

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self.box.connect("row-activated", self.on_row_activated)

    def set_content(self, log_text):

        self.box.remove_all()
        rows = self.parse_latex_log(log_text)
        for row in rows:
            self.box.append(row)

        if not rows:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("log")

    def on_row_activated(self, box, row):
        self.emit("scroll-to", row.line, row.text_before, row.text_after)

    def parse_latex_log(self, log_text):

        error_pattern = re.compile(r"! (.+?)\nl\.(\d+) (.+?)\n")
        warning_pattern = re.compile(r"LaTeX Warning: (.*?)(?:on input line (\d+))?\.\n")

        rows = []
        for error in error_pattern.findall(log_text):
            row = LatexLogRow(error[0] + ": " + error[2], True)
            row.line = int(error[1])
            row.text_before = error[2]
            rows.append(row)

        for warning in warning_pattern.findall(log_text):
            row = LatexLogRow(warning[0], False)
            if warning[1]:
                row.line = int(warning[1])
            rows.append(row)

        return rows


class LatexLogRow(Adw.ActionRow):
    def __init__(self, title, error = True):
        super().__init__()
        self.is_error = error
        self.line = 0
        self.set_title(title)
        self.text_before = ""
        self.text_after = ""
        self.set_activatable(True)
