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

<xsl:template match="presto:file">
    <div class="presto-line">
        <a class="presto-method" 
            href="{../@path}{@name}"
            ><xsl:value-of select="@name"/></a> [<xsl:value-of 
                select="@mime-type"/> | <xsl:value-of 
                select="@bytes"/> bytes]
    </div>
</xsl:template>

<xsl:template match="presto:dynamic/presto:file[@mime-type!='text/xml']"/>
                    
<xsl:template match="presto:dynamic/presto:directory">
    <div class="presto-line">
        <a class="presto-method" 
            href="?dynamic={../@path}{@name}/"
            ><xsl:value-of select="@name"/>/</a>
    </div>
</xsl:template>
            
<xsl:template match="presto:static/presto:directory">
    <div class="presto-line">
        <a class="presto-method" 
            href="?static={../@path}{@name}/"
            ><xsl:value-of select="@name"/>/</a>
    </div>
</xsl:template>
                
<xsl:template match="presto:dynamic">
    <div class="presto-line-head"><a 
        class="presto-method" href="?dynamic=/">/</a> Components</div>
    <div class="presto-box">
        <xsl:apply-templates select="presto:directory" />
        <xsl:apply-templates select="presto:file" />
    </div>
</xsl:template>    
    
<xsl:template match="presto:static">
    <div class="presto-line-head"><a
        class="presto-method" href="?static=/">/</a> Documents</div>
    <div class="presto-box">
        <xsl:apply-templates select="presto:directory" />
        <xsl:apply-templates select="presto:file" />
    </div>
</xsl:template>    
        
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
    
<xsl:template match="presto:module[@filename='root.py']"
    >
    <div class="presto-line" >
    <span class="presto-label" >root.py</span>
    </div>
</xsl:template>

<xsl:template match="presto:modules">
    <div class="presto-box">
        <div class="presto-line-head">Modules</div>
        <xsl:for-each select="*">
            <xsl:sort select="@filename" order="ascending" case-order = "lower-first"/>
            <xsl:apply-templates select="."/>
        </xsl:for-each>
    </div>
</xsl:template>

<xsl:template match="presto:root">    
    <div class="presto-top">
        <h1 style="font-weight: bold;"><a href="/index.html">Allegra</a> http://<xsl:value-of select="/presto:PRESTo/@presto-host"/></h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <div class="presto-body">
        <xsl:apply-templates/>
    </div>
</xsl:template>        
                    
<xsl:template match="/">
    <html>
    <head>
        <title>Allegra PRESTo</title>
        <link rel="stylesheet" href="/presto.css" type="text/css"/>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    </head>
    <body 
        style="font-family: 'Trebuchet MS', 'Lucida Grande', Verdana, Arial, Sans-Serif;"
        >
        <xsl:apply-templates/>
    </body>
    </html>    
</xsl:template>
        
</xsl:stylesheet>