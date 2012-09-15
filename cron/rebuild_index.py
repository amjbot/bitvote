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
        db.execute("INSERT web_index(term,uri,voice) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE dirty=0, voice=greatest(voice,%s)",
            term, content['uri'], web_share.voice, web_share.voice)
    #nltk.word_tokenize(sentence)

db.execute("DELETE FROM web_index WHERE dirty=1")



"""
CREATE TABLE IF NOT EXISTS web_index (
    term VARBINARY(512) NOT NULL,
    uri VARBINARY(512) NOT NULL,
    dirty DOUBLE NOT NULL DEFAULT 0,
    voice DOUBLE NOT NULL DEFAULT 1,
    PRIMARY KEY(term,uri)
);
"""
