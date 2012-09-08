import tornado.web
import tornado.database
import random
import string
import json
import hashlib


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def get_alias( access ):
    alias = db.get("SELECT * FROM speech WHERE source=%s and intent='alias' ORDER BY voice DESC LIMIT 1", access)
    alias = tornado.database.Row(json.loads(alias.content) if alias else {
        "codename": "",
        "location": "",
        "profile": "",
    })
    alias.fingerprint = hashlib.md5(access).hexdigest()
    return alias
def get_credentials( alias ):
    credentials = db.query("SELECT * FROM speech WHERE target=%s and intent='badge'", alias.fingerprint)
    return [ tornado.database.Row({
        "codename": alias.codename, "fingerprint": alias.fingerprint, "credential": row.content
    }) for row in credentials ]
def get_studentcredentials( alias ):
    credentials = db.query("SELECT * FROM speech WHERE source=%s and intent='badge'", alias.fingerprint)
    return [ tornado.database.Row({
        "codename": alias.codename, "fingerprint": alias.fingerprint, "credential": row.content
    }) for row in credentials ]

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
        credentials = get_credentials(alias)
        student_credentials = get_studentcredentials(alias)
        self.render( "private.html", access=access, alias=alias, credentials=credentials, student_credentials=student_credentials )


class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = json.dumps({
            "codename": self.get_argument("codename","Anonymous"),
            "location": self.get_argument("location",""),
            "profile": self.get_argument("profile",""),
        })
        db.execute( "DELETE FROM speech WHERE source=%s AND intent='alias'", access )
        db.execute( "INSERT speech(source,intent,content) VALUES(%s,'alias',%s)", access, alias)
        self.redirect("/"+access+"/private")

class badges_issue( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = get_alias(access)
        fingerprint = self.get_argument("fingerprint")
        credential = self.get_argument("credential")
        if not db.get("SELECT * FROM speech WHERE source=%s AND target=%s AND intent='badge' AND content=%s",
            alias.fingerprint, fingerprint, credential):
            db.execute( "INSERT speech(source,target,intent,content) VALUES(%s,%s,'badge',%s)", alias.fingerprint, fingerprint, credential )
        self.redirect("/"+access+"/private")

class badges_revoke( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = get_alias(access)
        fingerprint = self.get_argument("fingerprint")
        credential = self.get_argument("credential")
        db.execute( "DELETE FROM speech WHERE source=%s AND target=%s AND intent='badge' AND content=%s", alias.fingerprint, fingerprint, credential )
        self.redirect("/"+access+"/private")

