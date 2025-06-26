#!/usr/bin/env python3
import cgitb; cgitb.enable(display=1)     # show errors in-browser
try:
    from wsgiref.handlers import CGIHandler
    from app import app
    import traceback
    
    CGIHandler().run(app)
except Exception as err:
    print("Content-Type: text/html\n\n")
    print("ERROR:\n", traceback.format_exc())