import gi
gi.require_version("GtkSource", "5")
from gi.repository import GtkSource
from gi.repository import Gtk
import re


class LatexBuffer(GtkSource.Buffer):

    def __init__(self):
        super().__init__()

        language_manager = GtkSource.LanguageManager()
        latex = language_manager.get_language("latex")
        self.set_language(latex)
