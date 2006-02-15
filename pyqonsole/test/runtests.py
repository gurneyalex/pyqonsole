#!/usr/bin/python2.4
# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
from logilab.common.testlib import main

if __name__ == '__main__':
    import sys, os
    main(os.path.dirname(sys.argv[0]) or '.')
