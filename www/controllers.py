import tornado.web
import tornado.database
import random
import string
import json


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "index.html", access=access )


class bulletin( tornado.web.RequestHandler ):
    def get( self, access ):
        bulletin = [ tornado.database.Row({"title":"test", "body":"asdfasdfasdf"}),
                     tornado.database.Row({"title":"test", "body":"asdfasdfasdf"}) ]
        self.render( "bulletin.html", access=access, bulletin=bulletin )


class wiki( tornado.web.RequestHandler ):
    def get( self, access, page ):
        page_content = ""
        self.render( "wiki.html", access=access, page=page, page_content=page_content )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")


class web( tornado.web.RequestHandler ):
    def get( self, access ):
        result_set = []
        self.render( "web.html", access=access, result_set=result_set )
    def post( self ):
        pass


class profile( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "profile.html", access=access )
    def post( self ):
        pass

