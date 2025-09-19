import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self._file = None

    def set_path(self,path):
        self._file = Gio.File.new_for_path(path)
        self.reload()

    def show_empty(self):
        self.stack.set_visible_child_name("empty")

    def reload(self):
        if self._file.query_exists(None):
            self.stack.set_visible_child_name("content")
        else:
            self.stack.set_visible_child_name("empty")
