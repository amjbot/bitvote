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
        page = int(self.get_argument("page",0))
        topics = db.query("SELECT * FROM forum WHERE follow_hash IS NULL ORDER BY ts DESC LIMIT %s,20", 20*page)
        self.render( "bulletin.html", page=page, topics=topics, access=access )


class wiki( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "wiki.html", access=access )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")


class web( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "web.html", access=access )
    def post( self ):
        pass


class profile( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "profile.html", access=access )
    def post( self ):
        pass



