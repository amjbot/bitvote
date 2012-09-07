#!/usr/bin/env python

import controllers
import os.path
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.process
import sys

settings = dict(
   cookie_secret  = "65vtg78h9m097yn76vr64v7fbgn6tgmh79hm79ghmy879b7",
   static_path    = os.path.join(os.path.dirname(__file__), "static"),
   template_path  = os.path.join(os.path.dirname(__file__), "views" ),
   xsrf_cookies   = True
)

application = tornado.web.Application( [
    ( "^/(?P<access>[_0-9a-zA-Z]+)",                                controllers.index        ),
    ( "^/(?P<access>[_0-9a-zA-Z]+)/bulletin",                       controllers.bulletin     ),
    ( "^/(?P<access>[_0-9a-zA-Z]+)/wiki/(?P<page>.*)",              controllers.wiki         ),
    ( "^/(?P<access>[_0-9a-zA-Z]+)/web",                            controllers.web          ),
    ( "^/(?P<access>[_0-9a-zA-Z]+)/private",                        controllers.private      ),
    ( "^/(?P<access>[_0-9a-zA-Z]+)/alias-edit",                     controllers.alias_edit   ),
], **settings )


if __name__=="__main__":
    tornado.process.fork_processes(0)
    tornado.httpserver.HTTPServer(application, xheaders=True ).listen( 80 )
    tornado.ioloop.IOLoop.instance().start()
