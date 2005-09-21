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

<xsl:include href="presto.xsl"/>
    
<xsl:template match="presto:bsddb/presto:excp">
    <div style="font-family: -moz-fixed; background-color: #FFCCCC;"><xsl:value-of select="."/></div>
</xsl:template>

<xsl:template match="presto:presto|presto:bsddb">
<div class="presto-prompt-menu"
    ><a 
        href="?PRESTo=sync&amp;prompt=reactor.presto_vector"
        >sync</a> | <a 
        href="?PRESTo=async&amp;prompt=xdir()"
        >async</a></div>
</xsl:template>    

<xsl:template match="presto:bsddb-open">
    <div class="presto-top">
        <h1>BSDDB <span style="color: #BBBBBB;"
            >| <xsl:value-of select="/presto:PRESTo/@presto-path"/></span></h1>
    </div>
    <div class="presto-body">
        <form action="{/presto:PRESTo/@presto-path}">
            <div class="presto-line">
                <input name="name" type="text" size="42" value="{/presto:PRESTo/@name}"/> name
                <input name="type" type="text" size="6" value="{/presto:PRESTo/@type}"/> type
            </div>
            <div class="presto-line">
                <input name="PRESTo" type="submit" value="open"/>
            </div>
        </form>
    </div>
    <div class="presto-body">
        <xsl:apply-templates select="/presto:PRESTo/presto:bsddb/*"/>
    </div>
</xsl:template>
                                
<xsl:template match="presto:bsddb-get">
    <div class="presto-top">
        <h1>BSDDB <span style="color: #BBBBBB;"
            >| <xsl:value-of select="/presto:PRESTo/@presto-path"/></span></h1>
    </div>
    <div class="presto-body">
        <form action="{/presto:PRESTo/@presto-path}">
            <div class="presto-line">
                <input name="key" type="text" size="42" value="{/presto:PRESTo/@key}"/>
                <input name="PRESTo" type="submit" value="get"/>
            </div>
            <div class="presto-line">
                <input name="name" type="text" size="42" value="{/presto:PRESTo/@name}"/> name
                <input name="type" type="text" size="6" value="{/presto:PRESTo/@type}"/> type
            </div>
        </form>
    </div>
    <div class="presto-body">
        <xsl:apply-templates select="/presto:PRESTo/presto:bsddb/*"/>
    </div>
</xsl:template>
    
<xsl:template match="presto:bsddb-set">
    <div class="presto-top">
        <h1>BSDDB <span style="color: #BBBBBB;"
            >| <xsl:value-of select="/presto:PRESTo/@presto-path"/></span></h1>
    </div>
    <div class="presto-body">
        <form action="{/presto:PRESTo/@presto-path}">
            <div class="presto-line">
                <input name="key" type="text" size="42" value="{/presto:PRESTo/@key}"/>
                <input name="PRESTo" type="submit" value="set"/>
            </div>
            <div class="presto-line">
                <textarea name="value" type="text" cols="40" rows="10">
                    <xsl:value-of select="/presto:PRESTo/@value"/>
                </textarea>
            </div>
            <div class="presto-line">
                <input name="name" type="text" size="42" value="{/presto:PRESTo/@name}"/> name
                <input name="type" type="text" size="6" value="{/presto:PRESTo/@type}"/> type
            </div>
        </form>
    </div>
    <div class="presto-body">
        <xsl:apply-templates select="/presto:PRESTo/presto:bsddb/*"/>
    </div>
</xsl:template>
    
<xsl:template match="/">
    <html>
    <head>
        <title><xsl:value-of select="/presto:PRESTo/@presto-path"/></title>
        <link rel="stylesheet" href="/presto.css" type="text/css"/>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    </head>
    <body>
        <xsl:apply-templates/>
    </body>
    </html>    
</xsl:template>
        
</xsl:stylesheet>