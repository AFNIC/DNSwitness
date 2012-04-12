<?xml version='1.0' encoding='UTF-8'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:str="http://exslt.org/strings"
  exclude-result-prefixes = "str"
  version='1.0'>

  <xsl:template match="page">
    <xsl:variable name="title">
      <xsl:value-of select="@title"/>
    </xsl:variable>
    <xsl:variable name="pagetitle">
      <xsl:choose>
        <xsl:when test="@pagetitle">
          <xsl:value-of select="@pagetitle"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="@title"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <html xml:lang="en">
      <head>
        <link rel="stylesheet" type="text/css" href="http://www.dnswitness.net/dnswitness.css" />
        <title><xsl:value-of select="$projectname"/>: <xsl:value-of select="$title"/></title>
      </head>
      <body>
        <div>
        <h1 class="main-title"><xsl:value-of select="$pagetitle"/></h1>
        <xsl:apply-templates select="*"/>
        <hr class="before-footer"/>
        <p class="footer"><a href="index.html">Home</a>. Web site maintained by 
        <code><a href="mailto:webmaster@dnswitness.net">webmaster@dnswitness.net</a></code>. 
        Hosted by <a href="http://www.afnic.fr/">AFNIC</a>.
      </p>
      </div>
      </body>
    </html>
  </xsl:template>

  <xsl:template name="wikipedia">
    <xsl:param name="link"/>
    <xsl:param name="text"/>
    <xsl:variable name="actuallink">
      <xsl:choose>
        <xsl:when test="$link = ''">
          <xsl:value-of select="$text"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$link"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <a><xsl:attribute name="href">http://en.wikipedia.org/wiki/<xsl:value-of select="$actuallink"/></xsl:attribute><xsl:value-of select="$text"/></a>    
  </xsl:template>
  
  <xsl:template match="wikipedia">
    <xsl:variable name="word">
      <xsl:choose>
        <xsl:when test="@name">
          <xsl:value-of select="@name"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="text()"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="path">
       <xsl:choose>
          <xsl:when test="function-available('str:encode-uri')">      
            <xsl:value-of select="str:encode-uri($word, true())"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$word"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:variable>    
    <xsl:call-template name="wikipedia">
      <xsl:with-param name="link" select="$path"/>
      <xsl:with-param name="text" select="text()"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>