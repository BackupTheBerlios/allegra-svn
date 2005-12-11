<?xml version="1.0" encoding="us-ascii"?>
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

<!--

	This is the "main" PRESTo! XSL Transformation for an XHTML browser
	
	It provides style for the presto.PRESTo_prompt class, allowing 
	unfetered access to both the instance browsed and it's root
	modules.

	Developpers should use it as a template to develop new XSL
	transformations for their own instances first as they build
	them interactively, then for their own classes as their
	code moves from the prompt to a module.
	
	Note that this code has been tested only for Firefox 1.0.4, and
	may run only on most equivalent Mozilla browsers. I don't believe
	in proprietary API when it comes to a public network infrastructure
	like the world-wide-web.
		
	-->

<xsl:stylesheet
	version="1.1"
	xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
	xmlns:presto="http://presto/"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	>

<xsl:output method="xml" version="1.0" encoding="UTF-8"/>

<xsl:template match="xhtml:*">
    <xsl:copy-of select="."/>
</xsl:template>
    
<xsl:template match="presto:instance">
    <span style="presto-repr"
        >&lt;<xsl:value-of select="@type"/>&gt;</span>
</xsl:template>
           
<xsl:template match="presto:instance[@repr]">
    <span style="presto-repr"
        ><xsl:value-of select="@repr"/></span>
</xsl:template>
          
<xsl:template match="presto:str">
    <span class="presto-repr"
        ><xsl:value-of select="."/></span>
</xsl:template>
  
<xsl:template match="presto:str[@repr]">
    <span class="presto-repr"
        ><xsl:value-of select="@repr"/></span>
</xsl:template>
  
<xsl:template match="presto:str[@type='unicode']">
    <span class="presto-unicode"
        ><xsl:value-of select="."/></span>
</xsl:template>

<xsl:template match="presto:iter">
    <div style="font-family: -moz-fixed; color: grey;"
        ><xsl:value-of select="@type"/> (<xsl:for-each select="*"
            ><xsl:apply-templates select="."/>, </xsl:for-each>)</div>
</xsl:template>

<xsl:template match="presto:map">
    <table class="presto-map">
    <xsl:for-each select="presto:item"
        ><xsl:sort select="*[1]" order="ascending" case-order = "lower-first"
        /><tr class="presto-map-item"
        ><td class="presto-map-key"><xsl:apply-templates select="*[1]"
        /></td><td class="presto-map-value"><xsl:apply-templates select="*[2]"
        /></td></tr></xsl:for-each>
    </table>
</xsl:template>
    
<xsl:template match="presto:dir">
    <div style="font-family: -moz-fixed; color: grey;"
        >[<xsl:for-each select="*[2]/presto:str"
        ><xsl:sort order="ascending"
        /><a href="?PRESTo=async&amp;prompt=xdir({.})"
            ><xsl:value-of select="."/></a>, </xsl:for-each>]</div>
</xsl:template>
                
<xsl:template match="presto:dir[@base]">
    <xsl:variable name="base" select="@base"/>
    <xsl:apply-templates select="*[1]"/>
    <div style="border: 1px solid #EEEEEE; font-family: -moz-fixed; color: grey;"
        >[<xsl:for-each select="*[2]/presto:str"
            ><xsl:sort order="ascending"
                /><a href="?PRESTo=async&amp;prompt={$base}.{.}"
                    ><xsl:value-of select="."
                        /></a>, </xsl:for-each>]</div>
    <table class="presto-map">
        <xsl:for-each select="*[3]/presto:item">
            <xsl:sort select="*[1]" order="ascending" case-order = "lower-first"/>
            <tr class="presto-map-item">
                <td class="presto-map-key"
                    ><a href="?PRESTo=async&amp;prompt=xdir({$base}.{*[1]})"
                        style="font-family: -moz-fixed;"
                        ><xsl:value-of select="*[1]"/></a></td>
                <td class="presto-map-value"><xsl:apply-templates select="*[2]"
                    /></td>
            </tr>
        </xsl:for-each>
    </table>
</xsl:template>
        
<xsl:template match="presto:eval">
    <div class="presto-prompt-menu"
        ><a href="?PRESTo=async&amp;prompt=xdir()">xdir</a> |<a
        ><xsl:attribute name="href">?</xsl:attribute>presto</a>
    </div>
    <form class="presto-prompt-form" 
        method="GET" action="{/presto:PRESTo/@presto-path}"
        >
        <input name="prompt" type="text" size="82" value="{/presto:PRESTo/@prompt}"/>
        <input name="PRESTo" type="SUBMIT" value="{/presto:PRESTo/@PRESTo}"/>
    </form>
    <div class="presto-line"
        ><span style="padding-left: 4px; font-family: -moz-fixed; color: grey;"
            ><xsl:value-of select="/presto:PRESTo/@prompt"
            /></span></div>
    <div class="presto-prompt-return"><xsl:apply-templates /></div>            
</xsl:template>

<xsl:template match="presto:exec">
    <div class="presto-prompt-menu"
        ><a href="?PRESTo=async&amp;prompt=xdir()">xdir</a> |<a
        ><xsl:attribute name="href">?</xsl:attribute>presto</a>
    </div>
    <form class="presto-prompt-form" 
        method="GET" action="{/presto:PRESTo/@presto-path}"
        >
        <input name="prompt" type="text" size="82" value="{/presto:PRESTo/@prompt}"/>
        <input name="PRESTo" type="SUBMIT" value="{/presto:PRESTo/@PRESTo}"/>
    </form>
    <div class="presto-line"
        ><span style="padding-left: 4px; font-family: -moz-fixed; color: blue;"
            ><xsl:value-of select="/presto:PRESTo/@prompt"
            /></span></div>
    <div class="presto-prompt-return"><xsl:apply-templates /></div>            
</xsl:template>

<xsl:template match="presto:excp">
    <div class="presto-prompt-menu"
        ><a href="?PRESTo=async&amp;prompt=xdir()">xdir</a> |<a href="?">presto</a>
    </div>
    <form class="presto-prompt-form" 
        method="GET" action="{/presto:PRESTo/@presto-path}"
        >
        <input name="prompt" type="text" size="82" value="{/presto:PRESTo/@prompt}"/>
        <input name="PRESTo" type="SUBMIT" value="async"/>
    </form>
    <div class="presto-line"
        ><span style="padding-left: 4px; font-family: -moz-fixed; color: red;"
            ><xsl:value-of select="/presto:PRESTo/@prompt"
            /></span></div>
    <div class="presto-prompt-return">
        <table style="font-family: -moz-fixed;">
            <thead><tr><td colspan="3"  style="background-color: #FFCCCC;">
                <xsl:value-of select="presto:iter/presto:str[1]" />:
                <xsl:value-of select="presto:iter/presto:str[2]" />
            </td></tr></thead>
            <tbody>
                <xsl:for-each select="presto:iter/presto:iter/*">
                    <tr>
                        <td style="border-right: 1px solid #FFCCCC;">
                            <xsl:value-of select="*[1]"/>
                        </td>
                        <td style="border-right: 1px solid #FFCCCC;">
                            <xsl:value-of select="*[2]"/>
                        </td>
                        <td>
                            <xsl:value-of select="*[3]"/>
                        </td>
                    </tr>
                </xsl:for-each>
            </tbody>
        </table>
    </div>            
</xsl:template>

<xsl:template match="presto:presto">
<div class="presto-prompt-menu">
    <a href="?PRESTo=async&amp;prompt=xdir()">async</a>
</div>
</xsl:template>    

<xsl:template match="presto:async">
    <div class="presto-top">
        <h1 style="font-weight: bold;"
            >Async <span style="color: #BBBBBB;"
            ><xsl:value-of select="/presto:PRESTo/@presto-path"/></span></h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <xsl:apply-templates/>
</xsl:template>    
    
<xsl:template match="presto:sync">
    <div class="presto-top">
        <h1 style="font-weight: bold;"
            >Sync <span style="color: #BBBBBB;"
            ><xsl:value-of select="/presto:PRESTo/@presto-path"/></span></h1>
        <div style="font-size: small;">Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
    </div>
    <xsl:apply-templates/>
</xsl:template>    
    
<xsl:template match="/">
    <html>
        <head>
            <title><xsl:value-of select="/presto:PRESTo/@presto-path"/></title>
            <link rel="stylesheet" href="/presto.css" type="text/css"/>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        </head>
        <body
            style="font-family: 'Trebuchet MS', 'Lucida Grande', Verdana, Arial, Sans-Serif;"
            >
            <xsl:apply-templates />
        </body>
    </html>
</xsl:template>    

</xsl:stylesheet>