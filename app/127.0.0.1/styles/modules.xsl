<?xml version="1.0" encoding="utf-8"?>
<!--

	Copyright (C) 2005 Laurent A.V. Szyster

	This library is free software; you can redistribute it and/or modify
	it under the terms of version 2 of the GNU General Public License as
	published by the Free Software Foundation.

    http://www.gnu.org/copyleft/gpl.html

	This library is distributed in the hope that it will be useful, but
	WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

	You should have received a copy of the GNU General Public License
	along with this library; if not, write to the Free Software
	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
	USA

	-->

<xsl:stylesheet
	version="1.1"
	xmlns="http://www.w3.org/1999/xhtml"
	xmlns:presto="http://presto/"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	>

<xsl:output method="xml" version="1.0" encoding="UTF-8" />

<xsl:include href="/styles/presto.xsl"/>

<xsl:template match="presto:module[@loaded='no']"
    >
    <div class="presto-line" >
    <span class="presto-label" ><xsl:value-of select="@filename"
    /></span>[<a class="presto-method"
        ><xsl:attribute name="href"
        ><![CDATA[?PRESTo=load&filename=]]><xsl:value-of select="@filename"
        /></xsl:attribute>load</a>]
    </div>
</xsl:template>
            
<xsl:template match="presto:module[@loaded='yes']"
    >
    <div class="presto-line" >
    <span class="presto-label" ><xsl:value-of select="@filename"
        /></span>[<a class="presto-method"
        ><xsl:attribute name="href"
        ><![CDATA[?PRESTo=load&filename=]]><xsl:value-of select="@filename"
        /></xsl:attribute>reload</a>|<a class="presto-method"
        ><xsl:attribute name="href"
        ><![CDATA[?PRESTo=unload&filename=]]><xsl:value-of select="@filename"
        /></xsl:attribute>unload</a>]
    </div>
</xsl:template>

<xsl:template match="presto:modules">
    <div class="presto-box">
        <div class="presto-line-head">Modules</div>
        <xsl:for-each select="*">
          <xsl:sort select="@filename" order="ascending"
            case-order="lower-first"/>
          <xsl:apply-templates select="."/>
        </xsl:for-each>
    </div>
</xsl:template>
      
<xsl:template match="presto:PRESTo/presto:modules">
    <div class="presto-top">
        <h1><span style="font-weight: bold;"
            >PRESTo</span> Modules</h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <div class="presto-body">
      <div class="presto-box">
          <div class="presto-line-head">Modules</div>
          <xsl:for-each select="*">
            <xsl:sort select="@filename" order="ascending"
              case-order="lower-first"/>
            <xsl:apply-templates select="."/>
          </xsl:for-each>
      </div>
    </div>
</xsl:template>

<xsl:template match="/">
    <html>
    <head>
        <title>PRESTo/Modules</title>
        <link rel="stylesheet" href="/styles/presto.css" type="text/css"/>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    </head>
    <body>
        <xsl:apply-templates/>
    </body>
    </html>    
</xsl:template>
    
</xsl:stylesheet>