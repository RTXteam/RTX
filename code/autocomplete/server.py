import tornado.ioloop
import tornado.web
import os
#import sqlite3
import json
import sys
import rtxcomplete
import traceback

#class MainHandler(tornado.web.RequestHandler):
#    def get(self):
#        self.write("Hello, world")
#print __file__

root = os.path.dirname(os.path.abspath(__file__))
rtxcomplete.load()
#conn = sqlite3.connect('dict.db')
#conn.enable_load_extension(True)
#conn.load_extension("./spellfix")
#cursor = conn.cursor()

class autoSearch(tornado.web.RequestHandler):

    def get(self, arg,word=None):
        #print "match auto"
        try:
            limit = self.get_argument("limit")
            word = self.get_argument("word")
            callback = self.get_argument("callback") #jsonp

            result = rtxcomplete.prefix(word,limit)

            result = callback+"("+json.dumps(result)+");" #jsonp
            #result = json.dumps(result) #typeahead
            
            self.write(result)
            
        except:
            print(sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[2]
            self.write("error")

class fuzzySearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        #print "matched fuzzy"
        try:
            limit = self.get_argument("limit")
            word = self.get_argument("word")
            callback = self.get_argument("callback")
            #print word
            #cursor.execute("SELECT word FROM spell WHERE word MATCH \"" + word + "\" LIMIT " + limit)
            #cursor.execute("SELECT word FROM spell WHERE word MATCH \"" + word + "*\" LIMIT " + limit)
            result = rtxcomplete.fuzzy(word,limit);
            #rows = cursor.fetchall()
            #print type(rows)
            result = callback+"("+json.dumps(result)+");"
            #print arg, result
            #if (len(rows) > 0):
            self.write(result)
            #else:
            #self.write(callback+"("+json.dumps([["NO SUGGESTIONS"]])+");")
            #self.write(json.dumps(rows))
        except:
            print(sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[:]
            self.write("error")

class autofuzzySearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        #print "matched autofuzzy"
        try:
            limit = self.get_argument("limit")
            word = self.get_argument("word")
            callback = self.get_argument("callback")
            #print word
            #cursor.execute("SELECT word FROM spell WHERE word MATCH \"" + word + "\" LIMIT " + limit)
            #cursor.execute("SELECT word FROM spell WHERE word MATCH \"" + word + "*\" LIMIT " + limit)
            result = rtxcomplete.autofuzzy(word,limit);
            #rows = cursor.fetchall()
            #print type(rows)
            result = callback+"("+json.dumps(result)+");"
            #print arg, result
            #if (len(rows) > 0):
            self.write(result)
            #else:
            #self.write(callback+"("+json.dumps([["NO SUGGESTIONS"]])+");")
            #self.write(json.dumps(rows))
        except:
            print(sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[:]
            self.write("error")


class nodesLikeSearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        #try:
        if 1 == 1:
            limit = self.get_argument("limit")
            word = self.get_argument("word")
            callback = self.get_argument("callback")
            result = rtxcomplete.get_nodes_like(word,limit);
            result = callback+"("+json.dumps(result)+");"
            self.write(result)
        #except:
        #    print(sys.exc_info()[:])
        #    traceback.print_tb(sys.exc_info()[-1])
        #    self.write("error")


class defineSearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        print("matched define search: not implemented")
        self.write("")
            
def make_https_app():
    return tornado.web.Application([
        #(r"/", MainHandler),
        (r"/autofuzzy(.*)", autofuzzySearch),
        (r"/auto(.*)", autoSearch),
        (r"/fuzzy(.*)", fuzzySearch),
        (r"/define(.*)", defineSearch),
        (r"/nodeslike(.*)", nodesLikeSearch),
        (r"/(.*)", tornado.web.StaticFileHandler,
         {"path": root, "default_filename": "rtxcomplete.html"}),
    ],
        compress_response= True)

class redirect_handler(tornado.web.RequestHandler):
    def prepare(self):
        if self.request.protocol == 'http':
            if self.request.host == "rtxcomplete.ixlab.org":
                self.redirect('https://'+self.request.host, permanent=False)
                
    def get(self):
        self.write("Looks like you're trying to access rtxcomplete at the wrong host name.")
        self.write("<br>Please make sure the address is correct: 'rtxcomplete.ixlab.org'")

def make_redirect_app():
    return tornado.web.Application([
        (r'/', redirect_handler)
    ])

if __name__ == "__main__":
    print("root: " + root)

    if True: #FW/EWD: clean this up later
        http_app = make_https_app()
        http_server = tornado.httpserver.HTTPServer(http_app)
        http_server.listen(4999)

    else:
        redirect_app = make_redirect_app()
        redirect_app.listen(80)

        https_app = make_https_app()
        https_server = tornado.httpserver.HTTPServer(https_app, ssl_options={
            "certfile": "/etc/letsencrypt/live/rtxcomplete.ixlab.org/fullchain.pem",
            "keyfile" : "/etc/letsencrypt/live/rtxcomplete.ixlab.org/privkey.pem",
            })
        https_server.listen(443)

    tornado.ioloop.IOLoop.current().start()
