#!/usr/bin/env python

import tornado.database

db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")

quota = db.query("SELECT * FROM quota")
for q in quota:
    if q.universal:
        missing = db.query("SELECT * FROM access LEFT OUTER JOIN "
        "(SELECT * FROM license WHERE intent=%s) on "
        "access.access=license.access WHERE intent IS NULL", q.intent)
        for m in missing:
            db.execute("INSERT license(access,intent) VALUES(%s,%s)", m.access, m.intent)
    db.execute("UPDATE license SET entitlement=entitlement+%s WHERE intent=%s", q.duplicity, q.intent)


