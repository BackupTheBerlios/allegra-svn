# Copyright (C) 2005 Laurent A.V. Szyster
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
#    http://www.gnu.org/copyleft/gpl.html
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import sys


# produce a compact traceback data structure, ready to be serialized ...

def compact_traceback ():
        "return a compact traceback tuple"
        t, v, tb = sys.exc_info ()
        tbinfo = []
        assert tb # Must have a traceback ?
        while tb:
                tbinfo.append ((
                        tb.tb_frame.f_code.co_filename,
                        tb.tb_frame.f_code.co_name,
                        str (tb.tb_lineno)
                        ))
                tb = tb.tb_next
        del tb # just to be safe ?
        return t, v, tbinfo


def python_eval (co, env):
        """try to eval the compiled co in the environement env
        return either ('eval', result) or ('excp', traceback)"""
        try:
                return ('eval', eval (co, env))

        except Exception, excp:
                return ('excp', compact_traceback ())


def python_exec (co, env):
        """try to exec the compiled co in the environement env
        return either ('exec', None) or ('excp', traceback)"""
        try:
                exec co in env
        except Exception, excp:
                return ('excp', compact_traceback ())
                
        else:
                return ('exec', None)


def python_prompt (line, env):
        """try eval first, if that fails try exec, return ('eval', result) 
        ('exec', None) or ('excp', traceback)"""
        try:
                
                try:
                        co = compile (line, 'python_line', 'eval')
                except SyntaxError:
                        co = compile (line, 'python_line', 'exec')
                        method, result = python_exec (co, env)
                else:
                        method, result = python_eval (co, env)
        except Exception, excp:
                return ('excp', compact_traceback ())
                
        else:
                return (method, result)