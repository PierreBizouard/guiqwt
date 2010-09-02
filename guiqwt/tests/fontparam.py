# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""FontParam test"""

from guiqwt.styles import FontParam

SHOW = False # Do not show test in GUI-based test launcher

def test():
    fp = FontParam()
    fp.edit()
    fp.edit()

if __name__ == '__main__':
    import guidata
    guidata.qapplication()
    test()