#!/usr/bin/env python

import tornado.database
import time
import sys
import os.path

time_elapsed = time.time() - os.path.getmtime(__file__)
with file(__file__,'a'):
    os.utime(__file__,None)
db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


quota = db.query("SELECT * FROM timebank_quota")
for q in quota:
    if q.universal:
        missing = db.query("SELECT md5(access) as fingerprint FROM access LEFT OUTER JOIN "
        "(SELECT * FROM timebank WHERE currency=%s) as timebank on "
        "md5(access.access)=timebank.fingerprint WHERE currency IS NULL", q.currency)
        for m in missing:
            db.execute("INSERT timebank(fingerprint,currency) VALUES(%s,%s)", m.fingerprint, q.currency)
    db.execute("UPDATE timebank SET balance=balance+%s WHERE currency=%s", q.duplicity * time_elapsed, q.currency)


