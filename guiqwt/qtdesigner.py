# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
guiqwt QtDesigner helpers
"""


def loadui(fname, replace_class="QwtPlot"):
    """
    Return Widget or Window class from QtDesigner ui file 'fname'
    
    The loadUiType function (PyQt4.uic) doesn't work correctly with guiqwt
    QtDesigner plugins because they don't inheritate from a PyQt4.QtGui
    object.
    """
    from PyQt4.uic import loadUiType
    from StringIO import StringIO
    uifile_text = open(fname).read().replace(replace_class, "QFrame")
    ui, base_class = loadUiType( StringIO(uifile_text) )
    class Form(base_class, ui):
        def __init__(self, parent=None):
            super(Form, self).__init__(parent)
            self.setupUi(self)
    return Form


def compileui(fname, replace_class="QwtPlot"):
    from PyQt4.uic import compileUi
    from StringIO import StringIO
    uifile_text = open(fname).read().replace("QwtPlot", "QFrame")
    compileUi( StringIO(uifile_text), open(fname.replace(".ui","_ui.py"), 'w'),
               pyqt3_wrapper=True )
    
    
def create_qtdesigner_plugin(group, module_name, class_name, widget_options={},
                             icon=None, tooltip="", whatsthis=""):
    """Return a custom QtDesigner plugin class
    
    Example:
    create_qtdesigner_plugin(group = "guiqwt", module_name = "guiqwt.image",
                             class_name = "ImagePlotWidget", icon = "image.png",
                             tooltip = "", whatsthis = ""):
    """
    Widget = getattr(__import__(module_name, fromlist=[class_name]), class_name)
    from PyQt4.QtDesigner import QPyDesignerCustomWidgetPlugin
    from PyQt4.QtGui import QIcon
    from guidata.configtools import get_icon
    
    class CustomWidgetPlugin(QPyDesignerCustomWidgetPlugin):
        def __init__(self, parent = None):
            QPyDesignerCustomWidgetPlugin.__init__(self)
            self.initialized = False
    
        def initialize(self, core):
            if self.initialized:
                return
            self.initialized = True
    
        def isInitialized(self):
            return self.initialized
        
        def createWidget(self, parent):
            return Widget(parent, **widget_options)
        
        def name(self):
            return class_name
        
        def group(self):
            return group
        
        def icon(self):
            if icon is not None:
                return get_icon(icon)
            else:
                return QIcon()
            
        def toolTip(self):
            return tooltip
        
        def whatsThis(self):
            return whatsthis
        
        def isContainer(self):
            return False
        
        def domXml(self):
            return '<widget class="%s" name="%s" />\n' % (class_name,
                                                          class_name.lower())
        def includeFile(self):
            return module_name

    return CustomWidgetPlugin