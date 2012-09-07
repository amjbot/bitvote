import tornado.web
import tornado.database
import random
import string
import json
import hashlib


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def get_alias( access ):
    alias = db.get("SELECT * FROM speech WHERE source=%s and intent='alias' ORDER BY voice DESC", access)
    alias = tornado.database.Row(json.loads(alias.content) if alias else {
        "codename": "",
        "location": "",
        "profile": "",
    })
    alias.fingerprint = hashlib.md5(access).hexdigest()
    return alias


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        self.render( "index.html", access=access )


class bulletin( tornado.web.RequestHandler ):
    def get( self, access ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        bulletin = [ tornado.database.Row({"title":"test", "body":"asdfasdfasdf", "author":"Mr. Big"}),
                     tornado.database.Row({"title":"test", "body":"asdfasdfasdf", "author":"Mr. Big"}) ]
        self.render( "bulletin.html", access=access, bulletin=bulletin )


class wiki( tornado.web.RequestHandler ):
    def get( self, access, page ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        page_content = ""
        self.render( "wiki.html", access=access, page=page, page_content=page_content )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")


class web( tornado.web.RequestHandler ):
    def get( self, access ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        result_set = []
        self.render( "web.html", access=access, result_set=result_set )
    def post( self ):
        pass


class private( tornado.web.RequestHandler ):
    def get( self, access ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        alias = get_alias(access)
        self.render( "private.html", access=access, alias=alias )


class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = json.dumps({
            "codename": self.get_argument("codename","Anonymous"),
            "location": self.get_argument("location",""),
            "profile": self.get_argument("profile",""),
        })
        db.execute( "INSERT speech(source,intent,content) VALUES(%s,%s,%s)", access, "alias", alias)
        self.redirect("/"+access+"/private")
