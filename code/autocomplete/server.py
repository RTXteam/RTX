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
        #print "matched auto"
        try:
            limit = self.get_argument("limit")
            word = self.get_argument("word")
            callback = self.get_argument("callback")
            #print word
            result = rtxcomplete.prefix(word,limit)
            #cursor.execute("SELECT str FROM dict WHERE str like \"" + word + "%\" LIMIT " + limit)

            #rows = cursor.fetchall()
            #print type(rows)
            result = callback+"("+json.dumps(result)+");"
            #print arg, result
            #if (len(rows) > 0):
            self.write(result)
            #else:
            #    self.write(callback+"("+json.dumps([["NO SUGGESTIONS"]])+");")
            #self.write(json.dumps(rows))
        except:
            print (sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[2]
            self.write("error")

class fuzzySearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        #print "matched auto"
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
            print (sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[:]
            self.write("error")

class autofuzzySearch(tornado.web.RequestHandler):
    def get(self, arg,word=None):
        #print "matched auto"
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
            print (sys.exc_info()[:])
            traceback.print_tb(sys.exc_info()[-1])
            #print sys.exc_info()[:]
            self.write("error")
            
def make_app():
    return tornado.web.Application([
        #(r"/", MainHandler),
        (r"/autofuzzy(.*)", autofuzzySearch),
        (r"/auto(.*)", autoSearch),
        (r"/fuzzy(.*)", fuzzySearch),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": root, "default_filename": "index.html"}),
    ])

if __name__ == "__main__":
    print ("root: " + root)
    app = make_app()
    app.listen(80)
    tornado.ioloop.IOLoop.current().start()
