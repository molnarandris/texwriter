import gi
from gi.repository import Gtk, Adw

@Gtk.Template(resource_path='/io/github/molnarandris/TeXWriter/logviewer.ui')
class LogViewer(Gtk.Widget):
    __gtype_name__ = "LogViewer"

    stack = Gtk.Template.Child()
    box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

    def set_content(self, rows):
        if not rows:
            self.stack.set_visible_child_name("empty")
        else:
            self.stack.set_visible_child_name("log")

        self.box.remove_all()

        for row in rows:
            r = Adw.ActionRow()
            r.set_title(row.title)
            self.box.append(r)
