import tornado.web
import tornado.database
import random
import string
import json
import hashlib
import sys


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def get_fingerprint( access ):
    return tornado.database.Row({"fingerprint": hashlib.md5(access).hexdigest()})
def query_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent="", limit=50 ):
    speech = db.query("SELECT s.source AS source_fingerprint, s.target as target_fingerprint, s.content as s_content, " +
        "source.content AS source_alias, target.content AS target_alias from speech as s " +
        "LEFT OUTER JOIN speech AS source ON s.source=source.source AND (source.intent='alias' OR source.intent IS NULL) " +
        "LEFT OUTER JOIN speech AS target ON s.target=target.source AND (target.intent='alias' OR target.intent IS NULL) " +
        "WHERE %s IN (s.source,'') AND %s IN (s.target,'') AND %s IN (s.intent,'') ORDER BY s.voice desc LIMIT %s",
        source.fingerprint, target.fingerprint, intent, limit
    )
    print >> sys.stderr, dict(source=source, target=target, intent=intent), len(speech)
    for s in speech:
        s.update( json.loads(s.s_content) if s.s_content else {} )
        s.source = tornado.database.Row(json.loads(s.source_alias) if s.source_alias else {})
        s.target = tornado.database.Row(json.loads(s.target_alias) if s.target_alias else {})
    return speech
def get_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent=""):
    return (query_speech(source=source,target=target,intent=intent,limit=1) or [
    tornado.database.Row({"source_fingerprint":source.fingerprint, 
        "target_fingerprint": target.fingerprint, "intent":intent,
        "source": tornado.database.Row({}), "target":tornado.database.Row({})
    })])[0]
def put_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent="", content={} ):
    content = json.dumps(content)
    if not db.get("SELECT * FROM speech WHERE %s IN (source,'') AND %s IN (target,'') AND %s IN (intent,'') AND %s IN (content,'{}')",
        source.fingerprint, target.fingerprint, intent, content):
        db.execute( "INSERT speech(source,target,intent,content) VALUES(%s,%s,%s,%s)",
            source.fingerprint, target.fingerprint, intent, content )
def del_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent="", content={} ):
    content = json.dumps(content)
    db.execute("DELETE FROM speech WHERE %s IN (source,'') AND %s IN (target,'') AND %s IN (intent,'') AND %s IN (content,'{}')",
        source.fingerprint, target.fingerprint, intent, content )


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


class private( tornado.web.RequestHandler ):
    def get( self, access ):
        if not db.get("SELECT * FROM access WHERE access=%s", access):
            raise tornado.web.HTTPError(404)
        ident = get_fingerprint( access )
        alias = get_speech( source=ident, intent='alias' )
        credentials = query_speech( target=ident, intent='badge' )
        student_credentials = query_speech( source=ident, intent='badge' )
        contacts = query_speech( source=ident, intent='contact' )
        self.render( "private.html", access=access, alias=alias, credentials=credentials,
            student_credentials=student_credentials, contacts=contacts )


class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = get_fingerprint(access)
        del_speech(source=alias, intent="alias")
        put_speech(source=alias, intent="alias", content={
            "codename": self.get_argument("codename","Anonymous"),
            "location": self.get_argument("location",""),
            "profile": self.get_argument("profile",""),
        })
        self.redirect("/"+access+"/private")


class badges_issue( tornado.web.RequestHandler ):
    def post( self, access ):
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"credential": self.get_argument("credential")}
        put_speech(source=source, target=target, intent='badge', content=content) 
        self.redirect("/"+access+"/private")


class badges_revoke( tornado.web.RequestHandler ):
    def post( self, access ):
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"credential": self.get_argument("credential")}
        del_speech(source=source, target=target, intent='badge', content=content) 
        self.redirect("/"+access+"/private")


class contacts_remember( tornado.web.RequestHandler ):
    def post( self, access ):
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"keywords": self.get_argument("keywords"), 
                   "description": self.get_argument("description") }
        del_speech(source=source, target=target, intent='contact')
        put_speech(source=source, target=target, intent='contact', content=content)
        self.redirect("/"+access+"/private")


class contacts_forget( tornado.web.RequestHandler ):
    def post( self, access ):
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        del_speech(source=source, target=target, intent='contact') 
        self.redirect("/"+access+"/private")


