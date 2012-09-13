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
    speech = db.query("SELECT s.dchash AS document_hash, s.source AS source_fingerprint, s.target as target_fingerprint, " +
        "s.content as s_content, source.content AS source_alias, target.content AS target_alias, s.intent as intent " +
        "from speech as s " +
        "LEFT OUTER JOIN speech AS source ON s.source=source.source AND (source.intent='alias' OR source.intent IS NULL) " +
        "LEFT OUTER JOIN speech AS target ON s.target=target.source AND (target.intent='alias' OR target.intent IS NULL) " +
        "WHERE %s IN (s.source,'') AND %s IN (s.target,'') AND %s IN (s.intent,'') ORDER BY s.voice desc LIMIT %s",
        source.fingerprint, target.fingerprint, intent, limit
    )
    for s in speech:
        s.content = json.loads(s.s_content) if s.s_content else {}
        s.update( json.loads(s.s_content) if s.s_content else {} )
        s.source = tornado.database.Row(json.loads(s.source_alias) if s.source_alias else {})
        s.target = tornado.database.Row(json.loads(s.target_alias) if s.target_alias else {})
    return speech
def get_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent=""):
    speech = list(query_speech(source=source,target=target,intent=intent,limit=1))
    return (speech or [tornado.database.Row({"source_fingerprint":source.fingerprint, 
        "target_fingerprint": target.fingerprint, "intent":intent,
        "source": tornado.database.Row({}), "target":tornado.database.Row({})
    })])[0]
def put_speech( source=tornado.database.Row({'fingerprint':''}),
                target=tornado.database.Row({'fingerprint':''}), intent="", content={} ):
    content_string = json.dumps(content)
    if not db.get("SELECT * FROM speech WHERE %s IN (source,'') AND %s IN (target,'') AND %s IN (intent,'') AND %s IN (content,'{}')",
        source.fingerprint, target.fingerprint, intent, content_string):
        dchash = hashlib.md5(
          json.dumps(dict(content.items() + [('source',source.fingerprint),('target',target.fingerprint),('intent',intent)] ))
        ).hexdigest()
        db.execute( "INSERT IGNORE speech(source,target,intent,content,dchash) VALUES(%s,%s,%s,%s,%s)",
            source.fingerprint, target.fingerprint, intent, content_string, dchash )
def del_speech( source=tornado.database.Row({'fingerprint':''}), dchash="",
                target=tornado.database.Row({'fingerprint':''}), intent="", content={} ):
    content = json.dumps(content)
    db.execute("DELETE FROM speech WHERE %s IN (source,'') AND %s IN (target,'') AND %s IN (intent,'') " +
               "AND %s IN (content,'{}') AND %s IN (dchash,'')",
        source.fingerprint, target.fingerprint, intent, content, dchash )
def query_timebank( fingerprint=tornado.database.Row({'fingerprint':''}),
                    currency='' ):
    return db.query("SELECT * FROM timebank WHERE %s IN (fingerprint,'') AND %s in (currency,'')", fingerprint.fingerprint, currency)
def query_timebank_quota( currency='' ):
    return db.query("SELECT * FROM timebank_quota WHERE %s IN (currency,'')", currency)
def transfer_time( source, target, currency, amount ):
    if not db.get("SELECT * FROM timebank WHERE fingerprint=%s AND currency=%s AND balance>(%s * 1.003)", source.fingerprint, currency, amount):
        return False
    if not db.get("SELECT * FROM timebank WHERE fingerprint=%s AND currency=%s", target.fingerprint, currency):
        return False
    db.execute("UPDATE timebank set balance=balance-(%s * 1.003) WHERE fingerprint=%s AND currency=%s", amount, source.fingerprint, currency)
    db.execute("UPDATE timebank set balance=balance+%s WHERE fingerprint=%s AND currency=%s", amount, target.fingerprint, currency)
    return True

def require_access( access ):
    if not db.get("SELECT * FROM access WHERE access=%s", access):
        raise tornado.web.HTTPError(404)


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        require_access(access)
        ident = get_fingerprint( access )
        alias = get_speech( source=ident, intent='alias' )
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "index.html", access=access, alias=alias,
            timebank=timebank, timebank_quota=timebank_quota )


class bulletin( tornado.web.RequestHandler ):
    def get( self, access ):
        require_access(access)
        bulletin = query_speech( intent='bulletin' )
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "bulletin.html", access=access, bulletin=bulletin,
            timebank=timebank, timebank_quota=timebank_quota )

class bulletin_compose( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        content = {
            "subject": self.get_argument("subject",""),
            "message": self.get_argument("message",""),
            "voice": float(self.get_argument("voice","1.0")), }
        put_speech(source=source, intent='bulletin', content=content)
        self.redirect("/"+access+"/bulletin")


class wiki( tornado.web.RequestHandler ):
    def get( self, access, page ):
        require_access(access)
        page_content = ""
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "wiki.html", access=access, page=page, page_content=page_content,
            timebank=timebank, timebank_quota=timebank_quota )
    def post( self ):
        access = self.get_argument("access")
        follow = self.get_argument("follow",None)
        title = self.get_argument("title","")
        body = self.get_argument("body","")


class web( tornado.web.RequestHandler ):
    def get( self, access ):
        require_access(access)
        result_set = []
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "web.html", access=access, result_set=result_set,
            timebank=timebank, timebank_quota=timebank_quota )


class private( tornado.web.RequestHandler ):
    def get( self, access ):
        require_access(access)
        ident = get_fingerprint( access )
        alias = get_speech( source=ident, intent='alias' )
        credentials = query_speech( target=ident, intent='badge' )
        student_credentials = query_speech( source=ident, intent='badge' )
        contacts = query_speech( source=ident, intent='contact' )
        messages = query_speech( target=ident, intent='message' )
        documents = query_speech( source=ident )
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "private.html", access=access, alias=alias, credentials=credentials,
            student_credentials=student_credentials, contacts=contacts, messages=messages,
            documents=documents, timebank=timebank, timebank_quota=timebank_quota )


class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
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
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"credential": self.get_argument("credential")}
        put_speech(source=source, target=target, intent='badge', content=content) 
        self.redirect("/"+access+"/private")


class badges_revoke( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"credential": self.get_argument("credential")}
        del_speech(source=source, target=target, intent='badge', content=content) 
        self.redirect("/"+access+"/private")


class contacts_remember( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {"keywords": self.get_argument("keywords"), 
                   "description": self.get_argument("description") }
        del_speech(source=source, target=target, intent='contact')
        put_speech(source=source, target=target, intent='contact', content=content)
        self.redirect("/"+access+"/private")


class contacts_forget( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        del_speech(source=source, target=target, intent='contact') 
        self.redirect("/"+access+"/private")


class message_compose( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("fingerprint")})
        content = {
            "subject": self.get_argument("subject",""),
            "voice": float(self.get_argument("voice","1.0")),
            "message": self.get_argument("message",""),
        }
        put_speech(source=source, target=target, intent='message', content=content)
        self.redirect("/"+access+"/private")


class timebank_transfer( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = tornado.database.Row({"fingerprint": self.get_argument("recipient")})
        currency = self.get_argument("currency")
        amount = float(self.get_argument("amount"))
        transfer_time( source=source, target=target, currency=currency, amount=amount )
        self.redirect("/"+access+"/private")


class documents_remove( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        dchash = self.get_argument("hash")
        self.redirect("/"+access+"/private")
        del_speech( dchash=dchash )


class transport_import( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        for line in self.request.files['file'][0]['body'].split('\n'):
            if line.strip()=="":
                continue
            d = json.loads(line)
            content = json.loads(d['content'])
            dchash = hashlib.md5(
              json.dumps(dict(content.items() + [('source',d['source']),('target',d['target']),('intent',d['intent'])] ))
            ).hexdigest()
            db.execute("INSERT IGNORE speech(dchash,source,target,intent,voice,content) VALUES(%s,%s,%s,%s,%s,%s)",
              dchash, d['source'], d['target'], d['intent'], d['voice'], d['content'] )
        self.redirect("/"+access+"/private")


class transport_export( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access( access )
        ident = get_fingerprint( access )
        self.set_header('Content-Type', 'application/json')
        self.set_header('Content-Disposition', 'attachment; filename=documents.json')
        for d in db.query("SELECT source,target,intent,voice,content FROM speech WHERE source=%s", ident.fingerprint):
            self.write(json.dumps( d )+"\n")


class trade_propose( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access( access )
        ident = get_fingerprint( access )
        subject = self.get_argument("subject","")
        conditions = {}
        stakeholders = []
        for k in self.request.arguments:
            if not k.startswith('trade-type-'):
                continue
            n = k.split('-')[-1]
            conditions[n] = {'type': self.get_argument(k)}
            if conditions[n]['type'] == 'badge':
                conditions[n]['gain'] = self.get_argument('trade-gain-'+n)
                conditions[n]['mentor'] = self.get_argument('trade-mentor-'+n)
                conditions[n]['student'] = self.get_argument('trade-student-'+n)
                conditions[n]['credential'] = self.get_argument('trade-credential-'+n)
                stakeholders.append( conditions[n]['mentor'] )
                stakeholders.append( conditions[n]['student'] )
            elif conditions[n]['type'] == 'contact':
                conditions[n]['description'] = self.get_argument('trade-description-'+n)
                conditions[n]['contact'] = self.get_argument('trade-contact-'+n)
                conditions[n]['recipient'] = self.get_argument('trade-recipient-'+n)
                conditions[n]['keywords'] = self.get_argument('trade-keywords-'+n)
                stakeholders.append( conditions[n]['recipient'] )
            elif conditions[n]['type'] == 'message':
                conditions[n]['sender'] = self.get_argument('trade-sender-'+n)
                conditions[n]['message'] = self.get_argument('trade-message-'+n)
                conditions[n]['recipient'] = self.get_argument('trade-recipient-'+n)
                conditions[n]['subject'] = self.get_argument('trade-subject-'+n)
                stakeholders.append( conditions[n]['sender'] )
            elif conditions[n]['type'] == 'time':
                conditions[n]['currency'] = self.get_argument('trade-currency-'+n)
                conditions[n]['sender'] = self.get_argument('trade-sender-'+n)
                conditions[n]['recipient'] = self.get_argument('trade-recipient-'+n)
                conditions[n]['amount'] = self.get_argument('trade-amount-'+n)
                stakeholders.append( conditions[n]['sender'] )
                stakeholders.append( conditions[n]['recipient'] )
        trade = {'stakeholders': stakeholders, 'conditions': conditions.values()}
        for s in stakeholders:
            put_speech(source=ident, target=tornado.database.Row({"fingerprint": s}),
                       intent="trade-proposal", content=trade)
        self.redirect("/"+access+"/private")

