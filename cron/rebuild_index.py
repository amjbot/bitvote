#!/usr/bin/env python


import nltk
import tornado.database
import json

db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")

db.execute("UPDATE web_index set dirty=1")

def ngrams( tokens, n=3 ):
    for i in range(len(tokens)-1):
        for j in range(i+1,i+n):
            if j<=len(tokens):
                yield ' '.join(tokens[i:j])

for web_share in db.query("SELECT * FROM speech WHERE intent='web-share'"):
    content = json.loads(web_share.content)
    terms = nltk.word_tokenize( content['description'].lower() )
    for term in ngrams(terms):
        db.execute("INSERT web_index(term,uri,voice,description) VALUES(%s,%s,%s,%s) " +
            "ON DUPLICATE KEY UPDATE dirty=0, voice=greatest(voice,%s), description=if(voice<%s,%s,description)",
            term, content['uri'], web_share.voice, content['description'], web_share.voice, web_share.voice, content['description'])

db.execute("DELETE FROM web_index WHERE dirty=1")
