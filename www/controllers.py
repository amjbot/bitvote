import tornado.web
import tornado.database
import random
import string
import json
import hashlib
import sys


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def get_fingerprint( access ):
    return hashlib.md5(access).hexdigest()
def get_alias( access ):
    fingerprint = get_fingerprint(access)
    alias = db.get("SELECT * FROM speech WHERE source=%s and intent='alias' ORDER BY voice DESC LIMIT 1", fingerprint)
    alias = tornado.database.Row(json.loads(alias.content) if alias else {
        "codename": "",
        "location": "",
        "profile": "",
    })
    alias.fingerprint = fingerprint
    return alias
def get_credentials( alias ):
    credentials = db.query("SELECT s1.source as mentor,s1.target as student,s1.content as credential,s2.content as alias " +
        "FROM speech AS s1 JOIN speech AS s2 ON s1.source=s2.source AND (s2.intent='alias' OR s2.intent IS NULL)" +
        "WHERE s1.target=%s and s1.intent='badge'", alias.fingerprint)
    for c in credentials:
        c.update( json.loads(c.alias) if c.alias else {"codename":"","location":"","profile":""} )
    return credentials

def get_studentcredentials( alias ):
    credentials = db.query("SELECT s1.source as mentor,s1.target as student,s1.content as credential,s2.content as alias " +
        "FROM speech AS s1 JOIN speech AS s2 ON s1.target=s2.source AND (s2.intent='alias' OR s2.intent IS NULL)" +
        "WHERE s1.source=%s and s1.intent='badge'", alias.fingerprint)
    for c in credentials:
        c.update( json.loads(c.alias) if c.alias else {"codename":"","location":"","profile":""} )
    return credentials

def get_contacts( alias ):
    contacts = db.query("SELECT s1.target as contact, s2.content as alias, s1.content as s1_profile " +
        "FROM speech AS s1 JOIN speech AS s2 ON s1.target=s2.source AND (s2.intent='alias' OR s2.intent IS NULL) " +
        "WHERE s1.source=%s and s1.intent='contact'", alias.fingerprint)
    for c in contacts:
        print >> sys.stderr, c
        c.update( json.loads(c.alias) if c.alias else {"codename":"","location":"","profile":""} )
        c.update( json.loads(c.s1_profile) if c.s1_profile else {"keywords":"","description":""} )
    return contacts



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
        alias = get_alias(access)
        credentials = get_credentials(alias)
        student_credentials = get_studentcredentials(alias)
        contacts = get_contacts(alias)
        self.render( "private.html", access=access, alias=alias, credentials=credentials,
            student_credentials=student_credentials, contacts=contacts )


class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = json.dumps({
            "codename": self.get_argument("codename","Anonymous"),
            "location": self.get_argument("location",""),
            "profile": self.get_argument("profile",""),
        })
        fingerprint = get_fingerprint(access)
        db.execute( "DELETE FROM speech WHERE source=%s AND intent='alias'", fingerprint )
        db.execute( "INSERT speech(source,intent,content) VALUES(%s,'alias',%s)", fingerprint, alias)
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


class contacts_remember( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = get_alias(access)
        contact_fingerprint = self.get_argument("fingerprint")
        keywords = self.get_argument("keywords","")
        description = self.get_argument("description","")
        content = json.dumps({
            "keywords": keywords,
            "description": description,
        })
        if not db.get("SELECT * FROM speech WHERE source=%s AND target=%s AND intent='contact' AND content=%s",
            alias.fingerprint, contact_fingerprint, content):
            db.execute( "INSERT speech(source,target,intent,content) VALUES(%s,%s,'contact',%s)", alias.fingerprint, contact_fingerprint, content )
        self.redirect("/"+access+"/private")


class contacts_forget( tornado.web.RequestHandler ):
    def post( self, access ):
        alias = get_alias(access)
        contact_fingerprint = self.get_argument("fingerprint")
        db.execute("DELETE FROM speech WHERE source=%s and target=%s and intent='contact'", alias.fingerprint, contact_fingerprint)
        self.redirect("/"+access+"/private")

