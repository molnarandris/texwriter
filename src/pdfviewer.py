import gi
from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
import pymupdf

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        self._path = None

    def set_path(self,path):
        self._path = path
        self.reload()

    def show_empty(self):
        self.stack.set_visible_child_name("empty")

    def reload(self):
        try:
            document = pymupdf.open(self._path)
        except pymupdf.FileNotFoundError:
            self.stack.set_visible_child_name("empty")
            return

        self.stack.set_visible_child_name("content")
