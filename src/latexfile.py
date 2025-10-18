import gi
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib

import asyncio


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


class LatexFileError(Exception):
    pass

class LatexFile(GObject.Object):
    __gsignals__ = {
            'external-change': (
                GObject.SignalFlags.RUN_FIRST,  # flag
                None,  # return type
                ()  # arguments
            )
        }


    def __init__(self):
        super().__init__()
        self.file = None
        self.monitor = None

    def get_info(self):
        if self.file is None:
            display_name = "New file"
            directory = "unsaved"
        else:
            info = self.file.query_info("standard::display-name",
                                        Gio.FileQueryInfoFlags.NONE)
            if info:
                display_name = info.get_attribute_string("standard::display-name")
            else:
                display_name = self.file.get_basename()

            directory = self.file.get_parent().peek_path()

        return directory, display_name

    async def open_file(self,file):
        success, contents, etag = await file.load_contents_async(None)
        if not success:
            raise LatexFileError(f"Error opening {file.peek_path()}")

        try:
            text = contents.decode("utf-8")
        except UnicodeError as err:
            raise LatexFileError(f"The file {file.peek_path()} is not encoded in unicode")

        if self.monitor is not None:
            self.monitor.disconnect_by_func(self.file_monitor_cb)
        self.monitor = file.monitor(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self.file_monitor_cb)
        self.file = file

        return text

    async def save(self, text):
        self.monitor.handler_block_by_func(self.file_monitor_cb)
        contents = text.encode('utf-8')
        res = await self.file.replace_contents_async(contents, None, False,
                                                     Gio.FileCreateFlags.NONE, None)
        if not res:
            raise LatexFileError("Cannot save to {display_name}")
        await asyncio.sleep(0.1)
        self.monitor.handler_unblock_by_func(self.file_monitor_cb)

    def file_monitor_cb(self, monitor, file, other_file, event):
        if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            return
        self.emit("external-change")

    def get_path(self):
        if self.file is None:
            return None
        else:
            return self.file.peek_path()

    def get_dir(self):
        if self.file is None:
            return None
        else:
            return self.file.get_parent().peek_path()
