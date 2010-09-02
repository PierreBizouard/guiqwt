# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""
Interactive plotting interface with MATLAB-like syntax
"""

from PyQt4.QtGui import (QMainWindow, QPrinter, QPainter, QFrame, QVBoxLayout,
                         QGridLayout, QToolBar, QPixmap)
from PyQt4.QtCore import QRect, Qt

import guidata
from guidata.configtools import get_icon

# Local imports
from guiqwt.config import _
from guiqwt.plot import PlotManager
from guiqwt.image import ImagePlot
from guiqwt.curve import CurvePlot, PlotItemList
from guiqwt.histogram import ContrastAdjustment
from guiqwt.cross_section import XCrossSectionWidget, YCrossSectionWidget
from guiqwt.builder import make


_interactive = False
_figures = {}
_current_fig = None
_current_axes = None


class Window(QMainWindow):
    def __init__(self, wintitle):
        super(Window, self).__init__()
        self.default_tool = None
        self.plots = []
        self.itemlist = PlotItemList(None)
        self.contrast = ContrastAdjustment(None)
        self.xcsw = XCrossSectionWidget(None)
        self.ycsw = YCrossSectionWidget(None)
        
        self.manager = PlotManager(self)
        self.toolbar = QToolBar(_("Tools"), self)
        self.manager.add_toolbar(self.toolbar, id(self.toolbar))
        self.toolbar.setMovable(True)
        self.toolbar.setFloatable(True)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        frame = QFrame(self)
        self.setCentralWidget(frame)
        self.layout = QGridLayout()
        layout = QVBoxLayout(frame)
        frame.setLayout(layout)
        layout.addLayout(self.layout)
        self.frame = frame

        self.setWindowTitle(wintitle)
        self.setWindowIcon(get_icon('guiqwt.png'))

    def closeEvent(self, event):
        global _figures, _current_fig, _current_axes
        figure_title = unicode(self.windowTitle())
        if _figures.pop(figure_title) == _current_fig:
            _current_fig = None
            _current_axes = None
        self.itemlist.close()
        self.contrast.close()
        self.xcsw.close()
        self.ycsw.close()
        event.accept()
        
    def add_plot(self, i, j, plot):
        self.layout.addWidget(plot, i, j)
        self.manager.add_plot(plot, id(plot))
        self.plots.append(plot)

    def replot(self):
        for plot in self.plots:
            plot.replot()
            
    def add_panels(self, images=False):
        self.manager.add_panel(self.itemlist)
        if images:
            for panel in (self.ycsw, self.xcsw, self.contrast):
                panel.hide()
                self.manager.add_panel(panel)
            
    def register_tools(self, images=False):
        self.manager.register_standard_tools()
        self.manager.add_separator_tool()
        self.manager.register_curve_tools()
        if images:
            self.manager.register_image_tools()
            self.manager.add_separator_tool()
        self.manager.register_other_tools()
    
    def display(self):
        self.show()
        self.replot()
        self.manager.get_default_tool().activate()


class Figure(object):
    def __init__(self, title):
        self.axes = {}
        self.title = title
        self.win = None

    def get_axes(self, i, j):
        if (i,j) in self.axes:
            return self.axes[(i,j)]

        ax = Axes()
        self.axes[(i,j)] = ax
        return ax

    def build_window(self):
        _app = guidata.qapplication()
        self.win = Window(wintitle=self.title)
        images = False
        for (i, j), ax in self.axes.items():
            ax.setup_window(i, j, self.win)
            if ax.images:
                images = True
        self.win.add_panels(images=images)
        self.win.register_tools(images=images)

    def show(self):
        if not self.win:
            self.build_window()
        self.win.display()
        
    def save(self, fname, draft):
        ext = fname.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            _app = guidata.qapplication()
            if draft:
                mode = QPrinter.ScreenResolution
            else:
                mode = QPrinter.HighResolution
            printer = QPrinter(mode)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOrientation(QPrinter.Landscape)
            printer.setOutputFileName(fname)
            printer.setCreator('guiqwt.pyplot')
            self.print_(printer)
        elif ext == "png":
            if self.win is None:
                self.show()
            pixmap = QPixmap.grabWidget(self.win.centralWidget())
            pixmap.save(fname, 'PNG')
        
    def print_(self, device):
        if not self.win:
            self.build_window()
        W = device.width()
        H = device.height()
        from numpy import array
        coords = array(self.axes.keys())
        imin = coords[:,0].min()
        imax = coords[:,0].max()
        jmin = coords[:,1].min()
        jmax = coords[:,1].max()
        w = W/(jmax-jmin+1)
        h = H/(imax-imin+1)
        paint = QPainter(device)
        for (i,j), ax in self.axes.items():
            oy = (i-imin)*h
            ox = (j-jmin)*w
            ax.widget.print_(paint, QRect(ox, oy, w, h))
        

def do_mainloop(mainloop):
    global _current_fig
    assert _current_fig
    if mainloop:
        guidata.exec_qapplication_eventloop()
        

class Axes(object):
    def __init__(self):
        self.plots = []
        self.images = []
        self.last = None
        self.legend_position = None
        self.grid = False
        self.xlabel = ("", "")
        self.ylabel = ("", "")
        self.xcolor = ("black", "black") # axis label colors
        self.ycolor = ("black", "black") # axis label colors
        self.zlabel = None
        self.yreverse = False
        self.colormap = "jet"
        self.xscale = 'lin'
        self.yscale = 'lin'
        self.widget = None
        self.main_widget = None

    def add_legend(self, position):
        self.legend_position = position

    def set_grid(self, grid):
        self.grid = grid

    def add_plot(self, item):
        self.plots.append(item)
        self.last = item

    def add_image(self, item):
        self.images.append(item)
        self.last = item

    def setup_window(self, i, j, win):
        if self.images:
            plot = self.setup_image(i, j, win)
        else:
            plot = self.setup_plot(i, j, win)
        self.widget = plot
        plot.do_autoscale()

    def setup_image(self, i, j, win):
        p = ImagePlot(win, xlabel=self.xlabel, ylabel=self.ylabel,
                      zlabel=self.zlabel, yreverse=self.yreverse)
        self.main_widget = p
        win.add_plot(i, j, p)
        p.set_axis_color('bottom', self.xcolor[0])
        p.set_axis_color('top', self.xcolor[1])
        p.set_axis_color('left', self.ycolor[0])
        p.set_axis_color('right', self.ycolor[1])
        for item in self.images+self.plots:
            if item in self.images:
                item.set_color_map(self.colormap)
            p.add_item(item)
        if self.legend_position is not None:
            p.add_item(make.legend(self.legend_position))
        return p

    def setup_plot(self, i, j, win):
        p = CurvePlot(win, xlabel=self.xlabel, ylabel=self.ylabel)
        p.set_axis_color('bottom', self.xcolor[0])
        p.set_axis_color('top', self.xcolor[1])
        p.set_axis_color('left', self.ycolor[0])
        p.set_axis_color('right', self.ycolor[1])
        self.main_widget = p
        win.add_plot(i, j, p)
        for item in self.plots:
            p.add_item(item)
        p.enable_used_axes()

        active_item = p.get_active_item(force=True)
        p.set_scales(self.xscale, self.yscale)
        active_item.unselect()

        if self.legend_position is not None:
            p.add_item(make.legend(self.legend_position))

        if self.grid:
            p.gridparam.maj_xenabled = True
            p.gridparam.maj_yenabled = True
            p.gridparam.update_grid(p)
        return p
            

def _make_figure_title(N=None):
    global _figures
    if N is None:
        N = len(_figures)+1
    if isinstance(N, basestring):
        return N
    else:
        return "Figure %d" % N

def figure(N=None):
    """Create a new figure"""
    global _figures, _current_fig, _current_axes
    title = _make_figure_title(N)
    if title in _figures:
        f = _figures[title]
    else:
        f = Figure(title)
        _figures[title] = f
    _current_fig = f
    _current_axes = None
    return f

def gcf():
    """Get current figure"""
    global _current_fig
    if _current_fig:
        return _current_fig
    else:
        return figure()

def gca():
    """Get current axes"""
    global _current_axes
    if not _current_axes:
        axes = gcf().get_axes(1, 1)
        _current_axes = axes
    return _current_axes
 
def show(mainloop=True):
    """
    Show all figures and enter Qt event loop    
    This should be the last line of your script
    """
    global _figures, _interactive
    for fig in _figures.values():
        fig.show()
    if not _interactive:
        do_mainloop(mainloop)

def _show_if_interactive():
    global _interactive
    if _interactive:
        show()


def subplot(n, m, k):
    """
    Create a subplot command
    
    Example:
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    figure(1)
    subplot(2, 1, 1)
    plot(x, np.sin(x), "r+")
    subplot(2, 1, 2)
    plot(x, np.cos(x), "g-")
    show()
    """
    global _current_axes
    lig = (k-1)/m
    col = (k-1)%m
    fig = gcf()
    axe = fig.get_axes(lig,col)
    _current_axes = axe
    return axe

def plot(*args, **kwargs):
    """
    Plot curves
    
    Example:
    
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    plot(x, np.sin(x), "r+")
    plot(x, np.cos(x), "g-")
    show()
    """
    axe = gca()
    curve = make.mcurve(*args, **kwargs)
    axe.add_plot(curve)
    _show_if_interactive()

def plotyy(x1, y1, x2, y2):
    """
    Plot curves with two different y axes
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    plotyy(x, np.sin(x), x, np.cos(x))
    ylabel("sinus", "cosinus")
    show()
    """
    axe = gca()
    curve1 = make.mcurve(x1, y1, yaxis='left')
    curve2 = make.mcurve(x2, y2, yaxis='right')
    axe.ycolor = (curve1.curveparam.line.color, curve2.curveparam.line.color)
    axe.add_plot(curve1)
    axe.add_plot(curve2)
    _show_if_interactive()

def hist(data, bins=None, logscale=None, title=None, color=None):
    """
    Plot 1-D histogram
    
    Example:
        
    from numpy.random import normal
    data = normal(0, 1, (2000, ))
    hist(data)
    show()
    """
    axe = gca()
    curve = make.histogram(data, bins=bins, logscale=logscale,
                           title=title, color=color, yaxis='left')
    axe.add_plot(curve)
    _show_if_interactive()

def semilogx(*args, **kwargs):
    """
    Plot curves with logarithmic x-axis scale
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    semilogx(x, np.sin(12*x), "g-")
    show()
    """
    axe = gca()
    axe.xscale = 'log'
    curve = make.mcurve(*args, **kwargs)
    axe.add_plot(curve)
    _show_if_interactive()
    
def semilogy(*args, **kwargs):
    """
    Plot curves with logarithmic y-axis scale
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    semilogy(x, np.sin(12*x), "g-")
    show()
    """
    axe = gca()
    axe.yscale = 'log'
    curve = make.mcurve(*args, **kwargs)
    axe.add_plot(curve)
    _show_if_interactive()
    
def loglog(*args, **kwargs):
    """
    Plot curves with logarithmic x-axis and y-axis scales
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    loglog(x, np.sin(12*x), "g-")
    show()
    """
    axe = gca()
    axe.xscale = 'log'
    axe.yscale = 'log'
    curve = make.mcurve(*args, **kwargs)
    axe.add_plot(curve)
    _show_if_interactive()

def errorbar(*args, **kwargs):
    """
    Plot curves with error bars
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    errorbar(x, -1+x**2/20+.2*np.random.rand(len(x)), x/20)
    show()
    """
    axe = gca()
    curve = make.merror(*args, **kwargs)
    axe.add_plot(curve)
    _show_if_interactive()

def imshow(data):
    """
    Display the image in *data* to current axes
    
    Example:
        
    import numpy as np
    x = np.linspace(-5, 5, 1000)
    img = np.fromfunction(lambda x, y:
                          np.sin((x/200.)*(y/200.)**2), (1000, 1000))
    gray()
    imshow(img)
    show()
    """
    axe = gca()
    img = make.image(data)
    axe.add_image(img)
    axe.yreverse = True
    _show_if_interactive()

def pcolor(*args):
    """
    Create a pseudocolor plot of a 2-D array
    
    Example:
    
    import numpy as np
    r = np.linspace(1., 16, 100)
    th = np.linspace(0., np.pi, 100)
    R, TH = np.meshgrid(r, th)
    X = R*np.cos(TH)
    Y = R*np.sin(TH)
    Z = 4*TH+R
    pcolor(X, Y, Z)
    show()
    """
    axe = gca()
    img = make.pcolor(*args)
    axe.add_image(img)
    axe.yreverse = len(args) == 1
    _show_if_interactive()

def interactive(state):
    """Toggle interactive mode"""
    global _interactive
    _interactive = state

def ion():
    """Turn interactive mode on"""
    interactive(True)

def ioff():
    """Turn interactive mode off"""
    interactive(False)

#TODO: The following functions (title, xlabel, ...) should update an already 
#      shown figure to be compatible with interactive mode -- for now it just 
#      works if these functions are called before showing the figure
def title(text):
    """Set current figure title"""
    global _figures
    fig = gcf()
    _figures.pop(fig.title)
    fig.title = text
    _figures[text] = fig

def xlabel(bottom="", top=""):
    """Set current x-axis label"""
    assert isinstance(bottom, basestring) and isinstance(top, basestring)
    axe = gca()
    axe.xlabel = (bottom, top)

def ylabel(left="", right=""):
    """Set current y-axis label"""
    assert isinstance(left, basestring) and isinstance(right, basestring)
    axe = gca()
    axe.ylabel = (left, right)

def zlabel(label):
    """Set current z-axis label"""
    assert isinstance(label, basestring)
    axe = gca()
    axe.zlabel = label
    
def yreverse(reverse):
    """
    Set y-axis direction of increasing values
    
    reverse = False (default)
        y-axis values increase from bottom to top
    
    reverse = True
        y-axis values increase from top to bottom
    """
    assert isinstance(reverse, bool)
    axe = gca()
    axe.yreverse = reverse

def grid(act):
    """Toggle grid visibility"""
    axe = gca()
    axe.set_grid(act)

def legend(pos="TR"):
    """Add legend to current axes (pos='TR', 'TL', 'BR', ...)"""
    axe = gca()
    axe.add_legend(pos)

def colormap(name):
    """Set color map to *name*"""
    axe = gca()
    axe.colormap = name

def _add_colormaps(glbs):
    from guiqwt.colormap import get_colormap_list
    for cmap_name in get_colormap_list():
        glbs[cmap_name] = lambda name=cmap_name: colormap(name)
        glbs[cmap_name].__doc__ = "Set color map to '%s'" % cmap_name
_add_colormaps(globals())

def close(N=None, all=False):
    """Close figure"""
    global _figures, _current_fig, _current_axes
    if all:
        _figures = {}
        _current_fig = None
        _current_axes = None
        return
    if N is None:
        fig = gcf()
    else:
        fig = figure(N)
    fig.close()

def savefig(fname, draft=False):
    """
    Save figure
    
    Currently supports PDF and PNG formats only
    """
    ext = fname.rsplit(".", 1)[-1].lower()
    fig = gcf()
    if ext in ("pdf", "png"):
        fig.save(fname, draft)
    else:
        raise RuntimeError(_("Function 'savefig' currently supports "
                             ".pdf and .png formats only"))