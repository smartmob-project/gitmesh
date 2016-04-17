# -*- coding: utf-8 -*-


import pkg_resources

version = pkg_resources.resource_string('gitmesh', 'version.txt')
version = version.decode('utf-8').strip()
"""Package version (as a dotted string)."""
