import gi
from gi.repository import Gtk


class PdfViewer(Gtk.Widget):
    __gtype_name__ = "PdfViewer"

    def __init__(self):
        super().__init__()

