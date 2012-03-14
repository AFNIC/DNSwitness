#!/usr/bin/python

""" The Plugin base class: every DNSdelve module must inherit from
this class, or of one of its descendants"""

class Plugin:

    def __init__(self):
        self.zone_broken = False

    def config(self, **kwargs):
        pass
    
    def query(self, zone, nameservers):
        raise Exception("Class Plugin must be derived first!")

    def final(self):
        pass
    
if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")
