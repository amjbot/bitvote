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


def log_access( access, page, request ):
    headers = dict(
      (k,v) for (k,v) in request.headers.items() if can_json(v)
    )
    db.execute("INSERT INTO access(access,tag,comment) VALUES (%s,%s,%s)", access, page, json.dumps(headers))


class recruit( tornado.web.RequestHandler ):
    def get( self ):
        access = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        self.redirect( "/"+access )


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        log_access( access, "index", self.request )
        self.render( "index.html", access=access )


class forum( tornado.web.RequestHandler ):
    def get( self, access ):
        log_access( access, "forum", self.request )
        page = int(self.get_argument("page",0))
        topics = db.query("SELECT * FROM forum WHERE follow_hash IS NULL ORDER BY ts DESC LIMIT %s,20", 20*page)
        self.render( "forum.html", page=page, topics=topics, access=access )


class forum_create( tornado.web.RequestHandler ):
    def get( self, access ):
        log_access( access, "forum_create", self.request )
        self.render( "forum_create.html", access=access )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")

"""
DROP TABLE IF EXISTS forum;
CREATE TABLE IF NOT EXISTS forum (
    content_hash VARBINARY(32) NOT NULL,
    under_hash VARBINARY(32) NOT NULL,
    follow_hash VARBINARY(32) DEFAULT NULL,
    access VARBINARY(32) NOT NULL,
    tag VARBINARY(32) NOT NULL DEFAULT '',
    flag VARBINARY(32) NOT NULL DEFAULT '',
    title VARBINARY(512) NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '',
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY(under_hash)
);
"""

