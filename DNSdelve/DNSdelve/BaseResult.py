#!/usr/bin/python

""" The Result base class: every DNSdelve module must return objects
of this class, or of one of its descendants"""

class Result:

    def __init__(self):
        self.zone_broken = False

    def __str__(self):
        return "Result without displaying abilities"

    def store(self, uuid):
        pass
    
if __name__ == '__main__':
    raise Exception("Not yet usable as a main program, sorry")
