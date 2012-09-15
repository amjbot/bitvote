import tornado.web
import tornado.database
import tornado.escape
import random
import string
import json
import hashlib
import sys
import time
import pystache

db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


def get_fingerprint( access ):
    return tornado.database.Row({"fingerprint": hashlib.md5(access).hexdigest()})
def finger( fingerprint ):
    return tornado.database.Row({"fingerprint": fingerprint})
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
    return (speech or [None])[0]
def put_speech( source=tornado.database.Row({'fingerprint':''}), voice=1.0,
                target=tornado.database.Row({'fingerprint':''}), intent="", content={} ):
    content_string = json.dumps(content)
    if not db.get("SELECT * FROM speech WHERE %s IN (source,'') AND %s IN (target,'') AND %s IN (intent,'') AND %s IN (content,'{}')",
        source.fingerprint, target.fingerprint, intent, content_string):
        dchash = hashlib.md5(
          json.dumps(dict(content.items() + [('source',source.fingerprint),('target',target.fingerprint),('intent',intent)] ))
        ).hexdigest()
        db.execute( "INSERT IGNORE speech(source,target,intent,content,dchash,voice) VALUES(%s,%s,%s,%s,%s,%s)",
            source.fingerprint, target.fingerprint, intent, content_string, dchash, voice )
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

def require_access( access ):
    if not db.get("SELECT * FROM access WHERE access=%s", access):
        raise tornado.web.HTTPError(404)

def apply_timebank_tax( source, currency, amount ):
    if not db.get("SELECT * FROM timebank WHERE fingerprint=%s AND currency=%s AND balance>%s", source.fingerprint, currency, amount):
        return False
    db.execute("UPDATE timebank set balance=balance-%s WHERE fingerprint=%s AND currency=%s", amount, source.fingerprint, currency)
    return True
def has_timebank_funds( source, currency, amount ):
    if db.get("SELECT * FROM timebank WHERE fingerprint=%s AND currency=%s AND balance>%s", source.fingerprint, currency, amount):
        return True
    else:
        return False
def apply_timebank_debit( source, currency, amount ):
    db.execute("UPDATE timebank set balance=balance-%s WHERE fingerprint=%s AND currency=%s", amount, source.fingerprint, currency)
def apply_timebank_credit( source, currency, amount ):
    db.execute("UPDATE timebank set balance=balance+%s WHERE fingerprint=%s AND currency=%s", amount, target.fingerprint, currency)


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
        ident = get_fingerprint( access )
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
        ident = get_fingerprint( access )
        page_content = ""
        for w in query_speech( intent='wiki' ):
            if w.title == page:
                page_content = w.body
                break
        page_content = pystache.render( page_content, {"access": access})
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        self.render( "wiki.html", access=access, page=page, page_content=page_content,
            timebank=timebank, timebank_quota=timebank_quota )
class wiki_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        ident = get_fingerprint( access )
        title = self.get_argument("title")
        voice = float(self.get_argument("voice","1.0"))
        body = self.get_argument("body","")
        put_speech( source=ident, intent="wiki", voice=voice, content={"title":title, "body":body} )
        self.redirect("/"+access+"/wiki/"+tornado.escape.url_escape(title))


class web( tornado.web.RequestHandler ):
    def get( self, access ):
        require_access(access)
        ident = get_fingerprint( access )
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
        children = query_speech( source=ident, intent='parent' )
        documents = query_speech( source=ident )
        timebank = query_timebank( fingerprint=ident )
        timebank_quota = query_timebank_quota()
        open_trades = query_speech( target=ident, intent='trade-proposal' )
        rejected_trades = query_speech( target=ident, intent='trade-reject' )
        possible_trades = query_speech( target=ident, intent='trade-accept' )
        pending_trades = []
        accepted_trades = []
        for t in possible_trades:
             if db.query("SELECT * FROM speech WHERE intent='trade-reject' AND dchash=%s", t.document_hash):
                 rejected_trades.append( t )
             elif db.query("SELECT * FROM speech WHERE intent='trade-proposal' AND dchash=%s", t.document_hash):
                 pending_trades.append( t )
             else:
                 accepted_trades.append( t )
        self.render( "private.html", access=access, alias=alias, credentials=credentials,
            student_credentials=student_credentials, contacts=contacts, messages=messages,
            documents=documents, timebank=timebank, timebank_quota=timebank_quota,
            open_trades=open_trades, pending_trades=pending_trades, children=children,
            rejected_trades=rejected_trades, accepted_trades=accepted_trades )


def apply_alias_edit( source, codename="", location="", profile="" ):
    del_speech(source=source, intent="alias")
    put_speech(source=source, intent="alias", content={
        "codename": codename, "location": location, "profile": profile,
    })
class alias_edit( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        alias = get_fingerprint(access)
        apply_alias_edit( source=alias,
            codename=self.get_argument("codename","Anonymous"),
            location=self.get_argument("location",""),
            profile=self.get_argument("profile",""),
        )
        self.redirect("/"+access+"/private")


def apply_badges_issue( source, target, credential ):
    content = {"credential": credential}
    put_speech(source=source, target=target, intent='badge', content=content) 
class badges_issue( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("fingerprint") )
        apply_badges_issue( source=source, target=target, credential=self.get_argument("credential") )
        self.redirect("/"+access+"/private")


def apply_badges_revoke( source, target, credential ):
    content = {"credential": credential}
    del_speech(source=source, target=target, intent='badge', content=content) 
class badges_revoke( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("fingerprint") )
        apply_badges_revoke( source=source, target=target, credential=self.get_argument("credential") )
        self.redirect("/"+access+"/private")


def apply_contacts_remember( source, target, keywords, description ):
        content = {"keywords": keywords, "description": description}
        del_speech(source=source, target=target, intent='contact')
        put_speech(source=source, target=target, intent='contact', content=content)
class contacts_remember( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("fingerprint") )
        apply_contacts_remember( source=source, target=target, 
            keywords=self.get_arguments("keywords"),
            description=self.get_arguments("description") )
        self.redirect("/"+access+"/private")


def apply_contacts_forget( source, target ):
    del_speech(source=source, target=target, intent='contact')
class contacts_forget( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("fingerprint") )
        apply_contacts_forget( source=source, target=target )
        self.redirect("/"+access+"/private")


def apply_message_compose( source, target, subject, voice, message ):
    content = { "subject": subject, "message": message }
    put_speech(source=source, target=target, intent='message', content=content, voice=voice)
class message_compose( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("fingerprint") )
        apply_message_compose( source=source, target=target,
            subject = self.get_argument("subject",""),
            message = self.get_argument("message",""),
            voice = float(self.get_argument("voice","1.0")) )
        self.redirect("/"+access+"/private")


def apply_timebank_transfer( source, target, currency, amount ):
    tax_adjusted_amount = amount * 1.003
    if not has_timebank_funds( source=source, currency=currency, amount=tax_adjusted_amount ):
        return False
    apply_timebank_debit( source=source, currency=currency, amount=tax_adjusted_amount )
    apply_timebank_credit( source=source, currency=currency, amount=amount )
    return True
class timebank_transfer( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        source = get_fingerprint(access)
        target = finger( self.get_argument("recipient") )
        currency = self.get_argument("currency")
        amount = float(self.get_argument("amount"))
        if apply_timebank_transfer( source=source, target=target, currency=currency, amount=amount ):
            self.redirect("/"+access+"/private")
        else:
            self.redirect("/"+access+"/private?error=Transaction+was+not+completed+due+to+insufficient+funds.")


def apply_documents_remove( document_hash ):
    del_speech( dchash=document_hash )
class documents_remove( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access(access)
        apply_documents_remove( document_hash=self.get_argument("hash") )
        self.redirect("/"+access+"/private")


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
                conditions[n]['voice'] = self.get_argument('trade-voice-'+n)
                stakeholders.append( conditions[n]['sender'] )
            elif conditions[n]['type'] == 'time':
                conditions[n]['currency'] = self.get_argument('trade-currency-'+n)
                conditions[n]['sender'] = self.get_argument('trade-sender-'+n)
                conditions[n]['recipient'] = self.get_argument('trade-recipient-'+n)
                conditions[n]['amount'] = self.get_argument('trade-amount-'+n)
                stakeholders.append( conditions[n]['sender'] )
                stakeholders.append( conditions[n]['recipient'] )
        trade = {'stakeholders': stakeholders, 'conditions': conditions.values(), 'subject': subject, 'date': time.time()}
        for s in stakeholders:
            put_speech(source=ident, target=finger(s),
                       intent="trade-proposal", content=trade)
        self.redirect("/"+access+"/private")


class trade_reply( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access( access )
        ident = get_fingerprint( access )
        response = self.get_argument('response')
        trade = self.get_argument('trade')
        db.execute('UPDATE speech SET intent=%s WHERE target=%s AND dchash=%s',
            "trade-accept" if response=="accept" else "trade-reject", ident.fingerprint, trade )
        if all( s.intent=="trade-accept" for s in db.query("SELECT * FROM speech WHERE dchash=%s", trade) ):
            trade = json.loads(db.get('SELECT content FROM speech WHERE dchash=%s LIMIT 1',trade).content)
            for c in trade['conditions']:
                if c['type'] == 'time' and not \
                    has_timebank_funds( source=finger(c['sender']), currency=c['currency'], amount=c['amount'] ):
                    return self.redirect("/"+access+"/private?error=Transaction+was+not+completed+due+to+insufficient+funds.")
            for c in trade['conditions']:
                if c['type'] == 'badge':
                    if c['gain'] == 'gain':
                        apply_badges_issue( source=finger(c['mentor']), target=finger(c['student']), credential=c['credential'] )
                    else:
                        apply_badges_revoke( source=finger(c['mentor']), target=finger(c['student']), credential=c['credential'] )
                elif c['type'] == 'contact':
                    apply_contacts_remember( source=finger(c['recipient']), target=finger(c['contact']), 
                        keywords=c['keywords'], description=c['description'] )
                elif c['type'] == 'message':
                    apply_message_compose( source=finger(c['sender']), target=finger(c['recipient']),
                        subject=c['subject'], message=c['message'], voice=c['voice'] )
                elif c['type'] == 'time':
                    can_timebank_transfer( source=finger(c['sender']), target=finger(c['recipient']),
                        currency=c['currency'], amount=c['amount'] )
        self.redirect("/"+access+"/private")


class redirect( tornado.web.RequestHandler ):
    def get( self, redirect ):
        redirect_expire = get_speech(source=finger(redirect), intent='redirect-expire')
        if redirect_expire:
            del_speech(source=finger(redirect), intent='redirect-expire')
            self.redirect( redirect_expire.destination )
        else:
            raise tornado.web.HTTPError(410)


def apply_parent_spawn( parent, name ):
    child_access = ''.join( random.choice( string.letters + string.digits ) for _ in range(32) )
    tmp_redirect = ''.join( random.choice( string.letters + string.digits ) for _ in range(32) )
    child_ident = get_fingerprint( child_access )
    child_support = db.get("select sum(balance)/3 as child_support from timebank where currency='private'").child_support
    if has_timebank_funds( source=parent, currency='private', amount=child_support ):
        apply_timebank_debit( source=parent, currency='private', amount=child_support )
        db.execute("INSERT IGNORE access(access) VALUES(%s)", child_access)
        put_speech( source=parent, target=child_ident, intent='parent', content={'redirect':'/redirect/'+tmp_redirect} )
        put_speech( source=finger(tmp_redirect), intent='redirect-expire', content={'destination':'/'+child_access} )
        apply_alias_edit( source=child_ident, codename=name )
        return True
    return False
class parent_spawn( tornado.web.RequestHandler ):
    def post( self, access ):
        require_access( access )
        ident = get_fingerprint( access )
        name = self.get_argument("name","")
        if apply_parent_spawn( ident, name ):
            self.redirect("/"+access+"/private")
        else:
            self.redirect("/"+access+"/private?error=Transaction+was+not+completed+due+to+insufficient+funds.")
