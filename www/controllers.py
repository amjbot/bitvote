import tornado.web
import tornado.database


db = tornado.database.Connection(host="localhost",user="root",database="root",password="root")


class index( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "index.html", access=access )

class forum( tornado.web.RequestHandler ):
    def get( self, access ):
        self.render( "forum.html", access=access )
