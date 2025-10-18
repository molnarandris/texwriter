import gi
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk


latex_filter = Gio.ListStore.new(Gtk.FileFilter)

f = Gtk.FileFilter()
f.add_mime_type("text/x-tex")
latex_filter.append(f)

f = Gtk.FileFilter()
f.add_mime_type("text/plain")
latex_filter.append(f)

f = Gtk.FileFilter()
f.add_pattern("*")
f.set_name("All files")
latex_filter.append(f)

LATEX_FILTER = latex_filter

