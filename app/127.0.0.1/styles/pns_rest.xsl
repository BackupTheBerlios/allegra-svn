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
  xmlns:presto="http://presto/"
  xmlns:pns="http://pns/"
	xmlns:xhtml="http://www.w3.org/1999/xhtml"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  >

<xsl:output method="xml" version="1.0" encoding="UTF-8"/>    

<xsl:include href="/styles/presto.xsl"/>

<xsl:template match="pns:index|pns:context"> <a
    href="?PRESTo=articulate&amp;predicate={/presto:PRESTo/@predicate}&amp;context={.}">
  <xsl:value-of select="."/></a>, </xsl:template>

    
<xsl:template match="pns:index[@names]|pns:context[@names]"> [
  <xsl:apply-templates/><a
    href="?PRESTo=articulate&amp;predicate={/presto:PRESTo/@predicate}&amp;context={@names}">
  ...</a> ] </xsl:template>

    
<xsl:template
  match="presto:PRESTo/pns:index|presto:PRESTo/pns:context">
  <div>
    <xsl:apply-templates/> | <a
      href="?PRESTo=articulate&amp;predicate={/presto:PRESTo/@predicate}&amp;context={.}">
    index</a></div>
</xsl:template>

<xsl:template
  match="presto:PRESTo/pns:index[@names]|presto:PRESTo/pns:context[@names]">
  <div>
    <xsl:apply-templates/> | <a
      href="?PRESTo=articulate&amp;predicate={/presto:PRESTo/@predicate}&amp;context={@names}">
    index</a> </div>
</xsl:template>

<xsl:template match="item">
  <div style="font-size: small;">
    <h3 style="font-weight: bold;"><xsl:value-of select="title"/></h3>
    <span style="color: grey;">
      <xsl:value-of select="pubDate"/>
    </span>
    <div><xsl:value-of select="description"/> (...)</div>
    <a href="{link}"><xsl:value-of select="link"/></a>
  </div>
</xsl:template>
      
<xsl:template match="channel">
  <div style="font-size: small;">
    <h2 style="font-weight: bold;">
      <xsl:value-of select="title"/></h2>
    <xsl:value-of select="description"/>
    <xsl:apply-templates select="item"/>
  </div>
</xsl:template>
  
<xsl:template match="sat">
  <div>
    <xsl:value-of select="."/>
  </div>
</xsl:template>  
  
<xsl:template match="pns:articulate">
  <div class="presto-prompt-menu"
    ><a 
      href="?PRESTo=async&amp;prompt=xdir()"
      >async</a></div>
  <div class="presto-top">
    <h1>Meta<span 
        style="color: #006699;">base 4</span>RSS</h1>
    <div style="font-size: small; color: grey;"
      >Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
  </div>
  <div class="presto-body">
    <form action="{/presto:PRESTo/@presto-path}" method="GET">
      <div class="presto-line">
        <input name="context" type="text" size="62"
          value="{/presto:PRESTo/@context}"/>
        <input name="PRESTo" type="submit" value="articulate"/>
      </div>
      <div class="presto-line">
        <input name="predicate" type="text" size="62"
          value="{/presto:PRESTo/@predicate}"/>
      </div>
    </form>
  </div>
  <div class="presto-body" style="font-size: small; color: grey;">
    <xsl:apply-templates select="pns:index"/>
  </div>
  <div class="presto-body">
    <xsl:apply-templates select="./*[@context]"/>
  </div>
  <div 
    class="presto-box" 
    style="float: right; margin-left: 4px; margin-right: 16px; padding: 4px; text-align: right; font-size: small; background-color: #EEEEEE;"
    >
    <xsl:apply-templates select="pns:context"/>
  </div>
</xsl:template>    


<xsl:template match="presto:presto">
  <div class="presto-prompt-menu"
    ><a 
      href="?PRESTo=async&amp;prompt=xdir()"
      >async</a></div>
  <div class="presto-top">
    <h1><b>Allegra</b> PNS/REST</h1>
    <div style="font-size: small;"
      >Copyright 2005 Laurent A.V. Szyster | Copyleft GPL 2.0</div>
  </div>
  <div class="presto-body">
    <form action="{/presto:PRESTo/@presto-path}" method="GET">
      <div class="presto-line">
        <input name="context" type="text" size="62" value=""/>
        <input name="PRESTo" type="submit" value="articulate"/>
      </div>
    </form>
  </div>
</xsl:template>    


<xsl:template match="/">
  <html>
  <head>
    <title>Allegra PNS/REST</title>
    <link rel="stylesheet" href="/styles/presto.css"
      type="text/css"/>
    <meta http-equiv="Content-Type"
      content="text/html; charset=utf-8"/>
  </head>
  <body>
    <xsl:apply-templates/>
  </body>
  </html>    
</xsl:template>
    
</xsl:stylesheet>