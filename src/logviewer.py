import gi
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

    def set_content(self, rows):
        if not rows:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("log")

        self.box.remove_all()

        for row in rows:
            r = Adw.ActionRow()
            r.set_title(row.title)
            r.set_activatable(True)
            self.box.append(r)
            r.text_before = row.text_before
            r.text_after = row.text_after
            r.line = row.line

    def on_row_activated(self, box, row):
        self.emit("scroll-to", row.line, row.text_before, row.text_after)
        print("Scroll to signal emitted")
