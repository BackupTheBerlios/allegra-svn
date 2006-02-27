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

<xsl:stylesheet version="1.1" xmlns="http://www.w3.org/1999/xhtml"
  xmlns:presto="http://presto/"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  
  <xsl:output method="xml" version="1.0" encoding="UTF-8"/>
  
  <xsl:include href="/styles/presto.xsl"/>
  
  <xsl:template match="presto:form">
    <div class="presto-top">
      <h1><span style="font-weight: bold;">PRESTo</span>
        POST form data</h1>
      <div style="font-size: small;">Copyright 2005 Laurent A.V.
        Szyster | Copyleft GPL 2.0</div>
    </div>
    <div class="presto-body">
      <form method="POST" action="{/presto:PRESTo/@presto-path}">
        <input name="subject" type="text" size="62" tabindex="1"
          value="{/presto:PRESTo/@subject}"/>
        <input name="PRESTo" type="SUBMIT" tabindex="3"
          value="post"/>
        <textarea name="object" cols="60" rows="10" tabindex="2">
          <xsl:value-of select="/presto:PRESTo/@object"/>
        </textarea>
      </form>
    </div>
  </xsl:template>
  
</xsl:stylesheet>