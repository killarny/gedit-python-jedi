#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gi.repository import GObject, Gedit
try:
    import jedi
except ImportError:
    jedi = None

DEBUG = False

def document_is_python(document):
    if not document:
        return False
    uri = str(document.get_uri_for_display())
    if document.get_mime_type() == 'text/x-python' or \
        uri.endswith('.py') or uri.endswith('.pyw'):
            return True
    return False


class JediInstance(object):
    _title = "Jedi"

    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin

    def deactivate(self):
        self._window = None
        self._plugin = None


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
        self.update_completion(window)

    def on_active_tab_state_changed(self, window, data=None):
        self.update_completion(window)

    def update_completion(self, window):
        document = window.get_active_document()
        completion = self._instances.get(window)
        if not completion:
            if document_is_python(document):
                completion = JediInstance(self, window)
                self._instances[window] = completion
        elif not document_is_python(document):
            self._instances[window].deactivate()
            del self._instances[window]
            return None
        if completion:
            completion.update()
        return completion
