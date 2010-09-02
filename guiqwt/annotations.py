# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

import numpy as np
from math import fabs

from guidata.utils import update_dataset

# Local imports
from guiqwt.config import CONF, _
from guiqwt.styles import LabelParam, AnnotationParam
from guiqwt.shapes import (AbstractShape, RectangleShape, EllipseShape,
                           SegmentShape)
from guiqwt.label import DataInfoLabel
from guiqwt.interfaces import IShapeItemType, ISerializableType
from guiqwt.signals import SIG_ANNOTATION_CHANGED, SIG_ITEM_MOVED


class AnnotatedShape(AbstractShape):
    SHAPE_CLASS = None
    LABEL_ANCHOR = None
    def __init__(self, annotationparam=None):
        AbstractShape.__init__(self)
        assert self.LABEL_ANCHOR is not None
        self.shape = self.get_shape()
        self.label = self.get_label()
        self.position_and_size_visible = True
        if annotationparam is None:
            self.annotationparam = AnnotationParam(_("Annotation"),
                                                   icon="annotation.png")
        else:
            self.annotationparam = annotationparam
            self.annotationparam.update_annotation(self)
        
    def types(self):
        return (IShapeItemType, ISerializableType)
    
    def __reduce__(self):
        state = (self.shape, self.label, self.annotationparam)
        return (self.__class__, (), state)

    def __setstate__(self, state):
        shape, label, param = state
        self.shape = shape
        self.label = label
        self.annotationparam = param
        self.annotationparam.update_annotation(self)

    def set_style(self, section, option):
        self.shape.set_style(section, option)
        
    #----QwtPlotItem API--------------------------------------------------------
    def draw(self, painter, xMap, yMap, canvasRect):
        self.shape.draw(painter, xMap, yMap, canvasRect)
        if self.label.isVisible():
            self.label.draw(painter, xMap, yMap, canvasRect)
        
    #----Public API-------------------------------------------------------------
    def set_rect(self, x1, y1, x2, y2):
        self.shape.set_rect(x1, y1, x2, y2)
        self.set_label_position()

    def get_rect(self):
        return self.shape.get_rect()
    
    def get_shape(self):
        shape = self.SHAPE_CLASS(0, 0, 1, 1)
        shape.set_style("plot", "shape/drag")
        return shape
        
    def get_label(self):
        label_param = LabelParam(_("Label"), icon='label.png')
        label_param.read_config(CONF, "plot", "shape/label")
        label_param.anchor = self.LABEL_ANCHOR
        return DataInfoLabel(label_param, [self])
        
    def is_label_visible(self):
        return self.label.isVisible()
        
    def set_label_visible(self, state):
        self.label.setVisible(state)
        
    def update_label(self):
        self.label.update_text()

    def get_text(self):
        """Return text associated to current shape
        (see guiqwt.label.ObjectInfo)"""
        text = ""
        title = self.title().text()
        if title:
            text += "<b>%s</b>" % title
        subtitle = self.annotationparam.subtitle
        if subtitle:
            if text:
                text += "<br>"
            text += "<i>%s</i>" % subtitle
        if self.position_and_size_visible:
            if text:
                text += "<br>"
            text += self.get_position_and_size_text()
        return text
        
    def get_position_and_size_text(self):
        """Return formatted string with position and size of current shape"""
        raise NotImplementedError
        
    def set_label_position(self):
        """Set label position, for instance based on shape position"""
        raise NotImplementedError

    def apply_transform_matrix(self, x, y):
        V = np.array([x, y, 1.])
        W = np.dot(V, self.annotationparam.transform_matrix)
        return W[0], W[1]

    #----IBasePlotItem API------------------------------------------------------
    def hit_test(self, pos):
        return self.shape.poly_hit_test(self.plot(),
                                        self.xAxis(), self.yAxis(), pos)
            
    def move_point_to(self, handle, pos):
        self.shape.move_point_to(handle, pos)
        self.set_label_position()
        if self.plot():
            self.plot().emit(SIG_ANNOTATION_CHANGED, self)

    def move_shape(self, old_pos, new_pos):
        self.shape.move_shape(old_pos, new_pos)
        self.label.move_local_shape(old_pos, new_pos)
        
    def move_local_shape(self, old_pos, new_pos):
        old_pt = self.canvas_to_axes(old_pos)
        new_pt = self.canvas_to_axes(new_pos)
        self.shape.move_shape(old_pt, new_pt)
        self.set_label_position()
        if self.plot():
            self.plot().emit(SIG_ITEM_MOVED, self, *(old_pt+new_pt))
            self.plot().emit(SIG_ANNOTATION_CHANGED, self)

    def select(self):
        super(AnnotatedShape, self).select()
        self.shape.select()
    
    def unselect(self):
        super(AnnotatedShape, self).unselect()
        self.shape.unselect()

    def get_item_parameters(self, itemparams):
        self.shape.get_item_parameters(itemparams)
        self.label.get_item_parameters(itemparams)
        self.annotationparam.update_param(self)
        itemparams.add("AnnotationParam", self, self.annotationparam)
    
    def set_item_parameters(self, itemparams):
        self.shape.set_item_parameters(itemparams)
        self.label.set_item_parameters(itemparams)
        update_dataset(self.annotationparam, itemparams.get("AnnotationParam"),
                       visible_only=True)
        self.annotationparam.update_annotation(self)
    

def compute_center(x1, y1, x2, y2):
    return .5*(x1+x2), .5*(y1+y2)
    
def compute_rect_size(x1, y1, x2, y2):
    return x2-x1, fabs(y2-y1)

def compute_distance(x1, y1, x2, y2):
    return np.sqrt((x2-x1)**2+(y2-y1)**2)
    
def compute_angle(x1, y1, x2, y2, reverse=False):
    sign = -1 if reverse else 1
    return np.arctan(-sign*(y2-y1)/(x2-x1))*180/np.pi

class AnnotatedRectangle(AnnotatedShape):
    SHAPE_CLASS = RectangleShape
    LABEL_ANCHOR = "TL"
    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedShape.__init__(self, annotationparam)
        self.set_rect(x1, y1, x2, y2)
        
    def set_label_position(self):
        x_label, y_label = self.shape.points.min(axis=0)
        self.label.set_position(x_label, y_label)
    
    def get_transformed_coords(self, handle1, handle2):
        x1, y1 = self.apply_transform_matrix(*self.shape.points[handle1])
        x2, y2 = self.apply_transform_matrix(*self.shape.points[handle2])
        return x1, y1, x2, y2
                
    def get_infos(self):
        """Return dictionary with measured data on shape"""
        f = self.annotationparam.format
        coords = self.get_transformed_coords(0, 2)
        xc, yc = compute_center(*coords)
        dx, dy = compute_rect_size(*coords)
        return {
                'center': ( _("Center:"), f+u" ; "+f, (xc, yc) ),
                'size':   ( _("Size:"), f+u" x "+f, (dx, dy) )
                }
        
    def get_string_dict(self):
        sdict = {}
        for s_value, (name, format, value) in self.get_infos().iteritems():
            sdict[s_value+'_n'] = name
            sdict[s_value] = format % value
        return sdict
        
    def get_position_and_size_text(self):
        """Return formatted string with position and size of current shape"""
        tdict = self.get_string_dict()
        return u"%(center_n)s ( %(center)s )<br>%(size_n)s %(size)s" % tdict


class AnnotatedEllipse(AnnotatedRectangle):
    SHAPE_CLASS = EllipseShape
    LABEL_ANCHOR = "C"
    def __init__(self, x1=0, y1=0, x2=0, y2=0, ratio=1., annotationparam=None):
        self.ratio = ratio
        AnnotatedRectangle.__init__(self, x1, y1, x2, y2, annotationparam)
        
    def get_shape(self):
        shape = self.SHAPE_CLASS(0, 0, 1, 1, ratio=self.ratio)
        shape.set_style("plot", "shape/drag")
        return shape
        
    def set_label_position(self):
        x_label, y_label = self.shape.points.mean(axis=0)
        self.label.set_position(x_label, y_label)
        
    def get_infos(self):
        f = self.annotationparam.format
        xcoords = self.get_transformed_coords(0, 1)
        ycoords = self.get_transformed_coords(2, 3)
        xc, yc = compute_center(*xcoords)
        dx = compute_distance(*xcoords)
        dy = compute_distance(*ycoords)
        _x, yr1 = self.apply_transform_matrix(1., 1.)
        _x, yr2 = self.apply_transform_matrix(1., 2.)
        angle = (compute_angle(reverse=yr1 > yr2, *xcoords)+90)%180-90
        if fabs(angle) > 45:
            dx, dy = dy, dx
        return {
                'center': ( _("Center:"), f+u" ; "+f, (xc, yc) ),
                'size':   ( _("Size:"), f+u" x "+f, (dx, dy) ),
                'angle':  ( _("Angle:"), u"%.1f°", angle ),
                }
        
    def get_position_and_size_text(self):
        """Return formatted string with position and size of current shape"""
        tdict = self.get_string_dict()
        return u"%(center_n)s ( %(center)s )<br>" \
               u"%(size_n)s %(size)s<br>" \
               u"%(angle_n)s %(angle)s" % tdict


class AnnotatedCircle(AnnotatedEllipse):
    def __init__(self, x1=0, y1=0, x2=0, y2=0, annotationparam=None):
        AnnotatedEllipse.__init__(self, x1, y1, x2, y2, 1., annotationparam)
    
    def get_infos(self):
        f = self.annotationparam.format
        coords = self.get_transformed_coords(0, 1)
        xc, yc = compute_center(*coords)
        diameter = compute_distance(*coords)
        return {
                'center':   ( _("Center:"), f+u" ; "+f, (xc, yc) ),
                'diameter': ( _("Diameter:"), f, diameter )
                }
        
    def get_position_and_size_text(self):
        """Return formatted string with position and size of current shape"""
        tdict = self.get_string_dict()
        return u"%(center_n)s ( %(center)s )<br>" \
               u"%(diameter_n)s %(diameter)s" % tdict


class AnnotatedSegment(AnnotatedRectangle):
    SHAPE_CLASS = SegmentShape
    LABEL_ANCHOR = "C"
    def set_label_position(self):
        x0, y0 = self.shape.points[0]
        x2, y2 = self.shape.points[2]
        self.label.set_position(*compute_center(x0, y0, x2, y2))

    def get_infos(self):
        f = self.annotationparam.format
        distance = compute_distance(*self.get_transformed_coords(0, 2))
        return {'distance':   ( _("Distance:"), f, distance )}
        
    def get_position_and_size_text(self):
        """Return formatted string with position and size of current shape"""
        tdict = self.get_string_dict()
        return u"%(distance_n)s %(distance)s" % tdict