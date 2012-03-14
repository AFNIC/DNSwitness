# Question by Francis Dupont: find the non-ASCII QNAMEs which are encoded in UTF-8
# Algorithm: try to decode it as UTF-8, it if works, we assume it is UTF-8

# See nonascii.sql to create this file
ifile = open("non-ascii-qnames.txt")
l1_names = 0
utf8_names = 0
for line in ifile:
    utf8 = False
    line = line[:-1]
    name = unicode(line, "utf-8")
    try:
        l1 = name.encode("latin-1")
    except UnicodeEncodeError:
        utf8 = True
        l1 = name.encode("latin-1", 'replace')
    try:
        name = unicode(l1, "utf-8")
        utf8 = True
    except  UnicodeDecodeError:  
        name = unicode(l1, "latin-1")
    print "%s (%i chars)" % (name.encode("ascii", 'replace'), len(name))
    if utf8:
        utf8_names += 1
    else:
        l1_names += 1
print "%i UTF-8, %i Latin-1" % (utf8_names, l1_names)
