import tornado.web
import tornado.database
import random
import string
import json


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def can_json( v ):
    try:
        json.dumps(v)
        return True
    except:
        return False


class recruit( tornado.web.RequestHandler ):
    def get( self ):
        #TODO connect to one-time-use token from database
        access = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        self.redirect( "/"+access )


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "index.html", access=access )


class bbs( tornado.web.RequestHandler ):
    def get( self, access ):
        page = int(self.get_argument("page",0))
        topics = db.query("SELECT * FROM forum WHERE follow_hash IS NULL ORDER BY ts DESC LIMIT %s,20", 20*page)
        self.render( "forum.html", page=page, topics=topics, access=access )


class wiki( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "forum_create.html", access=access )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")
