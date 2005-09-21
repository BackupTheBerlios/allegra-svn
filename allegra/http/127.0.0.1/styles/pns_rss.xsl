<?xml version="1.0" encoding="ASCII"?>
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
<xsl:stylesheet version="1.1"
	xmlns="http://www.w3.org/1999/xhtml"
	xmlns:pns="http://pns/"
    xmlns:presto="http://presto/"
    xmlns:allegra="http://allegra/"
	xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    >

<xsl:output method="xml" version="1.0" encoding="UTF-8"/>    

<xsl:include href="/styles/presto.xsl"/>    

<!-- 0. Build a DB, risky with Mozilla? -->    
    
<xsl:key 
    name="pns-by-subject" 
    match="allegra:subject/pns:statement" 
    use="@subject" 
    />
    
<xsl:key
    name="sat-by-name"
    match="allegra:articulate/pns:statement"
    use="@subject"
    />
    
<!-- 1. the index templates -->
            
<xsl:template match="pns:index[@names]">
    [ <span
        ><xsl:apply-templates/><a 
            href="?PRESTo=articulate&amp;articulated={@names}"
            >...</a></span> ] 
</xsl:template>    
        
<xsl:template match="pns:index[@name]">
    <a 
        style="padding-left: 2px; padding-right: 2px;"
        href="?PRESTo=articulate&amp;articulated={@name}"
        > <xsl:value-of select="@name"/></a>, 
</xsl:template>

<xsl:template match="allegra:articulate/pns:index[@name]">
    <div class="presto-body" style="font-size: small; color: grey;">
        <xsl:apply-templates/><a 
            href="?PRESTo=articulate&amp;articulated={@name}"
            >...</a>
    </div>
</xsl:template>    
    
<xsl:template match="allegra:articulate/pns:index[@name='']">
    <div class="presto-body" style="font-size: small; color: grey;">
        <a 
            href="?PRESTo=articulate&amp;articulated="
            >...</a> 
    </div>
</xsl:template>    
    
<!-- 2. the context templates -->
                        
<xsl:template match="pns:context[@names]">
    <span
        ><xsl:apply-templates/><a 
            href="?PRESTo=articulate&amp;articulated={@names}"
            >...</a></span>
</xsl:template>        
        
<xsl:template match="pns:context[@name]">
    <a 
        style="padding-left: 2px; padding-right: 2px;"
        href="?PRESTo=articulate&amp;articulated={@name}"
        > <xsl:value-of select="@name"/></a>, 
</xsl:template>

<xsl:template match="allegra:articulate/pns:context[@names]">
    <xsl:variable 
        name="SAT" 
        select="key('sat-by-name', @names)"
        />
    <xsl:choose>
        <xsl:when test="not ($SAT)">
            <div><xsl:apply-templates/><a 
                    href="?PRESTo=articulate&amp;articulated={@names}"
                    >...</a></div>
        </xsl:when>
        <xsl:otherwise>
            <div
                ><a 
                    href="?PRESTo=articulate&amp;articulated={@names}"
                    ><xsl:value-of select="$SAT"/></a></div>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>    
        
<xsl:template match="allegra:articulate/pns:context[@name]">
    <div><a 
        style="padding-left: 2px; padding-right: 2px;"
        href="?PRESTo=articulate&amp;articulated={@name}"
        > <xsl:value-of select="@name"/></a></div>
</xsl:template>

<!-- 3. Objects, to subclass for something else than RSS (what about auto-load?) -->    

<xsl:template match="allegra:subject">
    <xsl:variable 
        name="SUBJECTS" 
        select="key('pns-by-subject', pns:statement[1]/@subject)"
        />
    <div 
        class="presto-body" 
        >
        <div>
            <a  
                style="font-weight: bold;"
                href="{$SUBJECTS[@predicate='link']}"
                ><xsl:copy-of select="$SUBJECTS[@predicate='title'][1]"/></a>
        </div>
        <div 
            style="font-size: small; font-weight: bold;"
            >
            <xsl:copy-of select="$SUBJECTS[@predicate='pubDate'][1]"/>
        </div>
        <div 
            style="color: grey; font-size: small;"
            > 
            <xsl:value-of select="$SUBJECTS[@predicate='link'][1]"/>
        </div>
        <div 
            style="font-size: small;"
            > 
            <xsl:value-of select="$SUBJECTS[@predicate='description'][1]"/>
        </div>
    </div>
</xsl:template>    

<xsl:template match="allegra:articulate|presto:presto">
    <div class="presto-prompt-menu"
        ><a 
            href="/root.xml"
            >root</a> | <a 
            href="?PRESTo=async&amp;prompt=xdir()"
            >async</a> | <a href="?">presto</a></div>
    <div class="presto-top">
        <h1 style="font-weight: bold;"
            ><a href="/index.html">Allegra</a> for RSS</h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <div class="presto-body">
        <form action="{/presto:PRESTo/@presto-path}">
            <div class="presto-line">
                <input name="articulated" type="text" size="52" value=""/>
                <input name="PRESTo" type="submit" value="articulate"/>
                <xsl:if test="/presto:PRESTo/@articulated!=''">
                    <a 
                        style="padding-left: 8px; padding-right: 8px;"
                        href="?PRESTo=articulate&amp;predicate=comment&amp;subject={/presto:PRESTo/@articulated}"
                        >post</a>
                </xsl:if>
            </div>
        </form>
    </div>
    <div 
        class="presto-box" 
        style="float: right; margin-left: 4px; margin-right: 16px; padding: 4px; text-align: right; font-size: small; background-color: #EEEEEE;"
        >
        <xsl:apply-templates select="pns:context"/>
    </div>
    <div class="presto-body" style="font-size: small; color: grey;">
        <xsl:apply-templates select="pns:index"/>
    </div>
    <xsl:apply-templates select="allegra:subject[pns:statement/@predicate='item']"/>
    <div class="presto-body" style="font-size: small; color: grey;">
        <xsl:for-each select="pns:statement[@predicate='sat']">
            <div><a href="?PRESTo=articulate&amp;articulated={@subject}"><xsl:value-of select="."/></a></div>
        </xsl:for-each>
    </div>
</xsl:template>    

<xsl:template match="allegra:post">
    <div class="presto-prompt-menu"
        ><a 
            href="/root.xml"
            >root</a> | <a 
            href="?PRESTo=async&amp;prompt=xdir()"
            >async</a> | <a href="?">presto</a></div>
    <div class="presto-top">
        <h1 style="font-weight: bold;"
            ><a href="/index.html">Allegra</a> for RSS</h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <div class="presto-body">
        <form action="{/presto:PRESTo/@presto-path}">
            <div class="presto-line">
                <input name="subject" type="text" size="52" value="{/presto:PRESTo/@subject}"/> subject
                <input name="PRESTo" type="submit" value="post"/>
            </div>
            <div class="presto-line">
                <input name="predicate" type="text" size="52" value="{/presto:PRESTo/@predicate}"/> predicate
            </div>
            <div class="presto-line">
                <input name="object" type="text" size="52" value="{/presto:PRESTo/@object}"/> object
            </div>
            <div class="presto-line">
                <input name="context" type="text" size="52" value="{/presto:PRESTo/@context}"/> context
            </div>
        </form>
    </div>
    <xsl:apply-templates/>
</xsl:template>    

<xsl:template match="/">
    <html>
    <head>
        <title>Allegra PNS - The Semantic Peer</title>
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