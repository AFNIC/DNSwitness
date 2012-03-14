<?xml version='1.0' encoding='UTF-8'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:str="http://exslt.org/strings"
  exclude-result-prefixes = "str"
  version='1.0'>

  <xsl:import href="../../library.xslt"/>
  
  <xsl:param name="projectname">DNSmezzo</xsl:param>

  <xsl:output method = "xml"
    encoding = "UTF-8"
    omit-xml-declaration = "no"
    doctype-system = "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
    doctype-public = "-//W3C//DTD XHTML 1.0 Strict//EN"
    indent = "yes"/>
  
</xsl:stylesheet>
