#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gi.repository import Gtk, GObject, Gedit
try:
    import jedi
except ImportError:
    jedi = None

DEBUG = False


class JediInstance(object):
    _title = "Jedi"

    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        self._document = self._window.get_active_document()
        self._view = Gedit.Tab.get_from_document(self._document).get_view()
        self._handlers = []
        self._handlers.append(
            self._document.connect('notify', self.on_notify))
        self._handlers.append(
            self._view.connect('key-press-event', self.on_view_keypress))

    def deactivate(self):
        for handler_id in self._handlers[:]:
            self._document.disconnect(handler_id)
            self._handlers.remove(handler_id)
        self._window = None
        self._plugin = None

    def on_notify(self, document, *data):
        """The document has changed in some way. (Loaded, edited, etc)
        """
        if document != self._document:
            raise ValueError("Document in signal doesn't match instance!")
        # TODO: show completions in a non-annoying manner (wait for ctrl-space?)

    def on_view_keypress(self, view, event):
        """User pressed a key in the document.
        """
#        if view != self._view:
#            raise ValueError("View in signal doesn't match instance!")
        char = unicode(event.string)
        # don't complete when pasting text
        if len(char) > 1:
            return
        # only trigger completions on a dot(.)
        if char == u'.':
            self.show_completion()

    def selected(self):
        """This instance has just been selected.
        """
        # TODO: show completions in a non-annoying manner (wait for ctrl-space?)
        pass

    def cursor_position(self):
        """Returns the cursor position as a tuple.
        """
        g_iter = self._document.get_iter_at_mark(self._document.get_insert())
        line = g_iter.get_line() + 1
        col = g_iter.get_line_offset()
        return line, col

    def cursor_coords(self, convert_to_window=True):
        """Returns the cursor coords as a tuple.

        Convert relative to window if convert_to_window is specified.
        """
        g_iter = self._document.get_iter_at_mark(self._document.get_insert())
        rect = self._view.get_iter_location(g_iter)
        if convert_to_window:
            x, y = self._view.buffer_to_window_coords(
                Gtk.TextWindowType.WIDGET, rect.x, rect.y)
            return self._view.translate_coordinates(self._window, x, y)
        return rect.x, rect.y

    def show_completion(self):
        """Show the completion interface, if needed.
        """
        # if the document is untouched (not changed since last save),
        ## then we don't need completion
        if self._document.is_untouched():
            return

        # filepath of the document being edited
        filepath = self._document.get_uri_for_display()

        # get the source of the document
        start, end = self._document.get_bounds()
        source = self._document.get_text(start, end, False)

        # find the cursor position
        line, col = self.cursor_position()

        # begin jedi mind-control tricks
        script = jedi.Script(source, line, col, filepath)
        call_def = script.get_in_function_call()
        completions = script.complete()

        # bail out if there aren't any completions to show
        if not completions:
            return

        # figure out where to display the completion window
        cursor_x, cursor_y = self.cursor_coords()
        # TODO: refine and display completions


class JediPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = 'JediPlugin'
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._instances = {}

    def do_activate(self):
        self._handlers = []
        self._handlers.append(self.window.connect(
            'tab-removed', self.on_tab_removed))
        self._handlers.append(self.window.connect(
            'active-tab-changed', self.on_active_tab_changed))
        self._handlers.append(self.window.connect(
            'active-tab-state-changed', self.on_active_tab_state_changed))

    def do_deactivate(self):
        for handler_id in self._handlers[:]:
            self.window.disconnect(handler_id)
            self._handlers.remove(handler_id)

    def on_tab_removed(self, window, tab, data=None):
        if window not in self._instances.keys():
            return
        if not window.get_active_tab():
            self._instances[window].deactivate()
            del self._instances[window]

    def on_active_tab_changed(self, window, tab, data=None):
        self.select_completion(window)

    def on_active_tab_state_changed(self, window, data=None):
        self.select_completion(window)

    def select_completion(self, window):
        document = window.get_active_document()
        completion = self._instances.get(window)
        if not completion:
            if self.document_is_python(document) and \
                    self.needs_completion(document):
                completion = JediInstance(self, window)
                self._instances[window] = completion
        elif not self.document_is_python(document) or \
                not self.needs_completion(document):
            self._instances[window].deactivate()
            del self._instances[window]
            return None
        if completion:
            completion.selected()
        return completion

    def document_is_python(self, document):
        if not document:
            return False
        uri = str(document.get_uri_for_display())
        if document.get_mime_type() == 'text/x-python' or \
            uri.endswith('.py') or uri.endswith('.pyw'):
                return True
        return False

    def needs_completion(self, document):
        # if jedi didn't get imported, don't attempt completion
        if not jedi:
            return False
        # if the document is readonly, don't bother with completion
        if document.get_readonly():
            return False
        return True
