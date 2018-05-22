import sqlite3

conn = None
cursor = None

def load():
    global conn
    global cursor
    conn = sqlite3.connect('dict.db')
    conn.enable_load_extension(True)
    conn.load_extension("./spellfix")
    cursor = conn.cursor()
    return True

def prefix(word,limit):
    cursor.execute("SELECT str FROM dict WHERE str LIKE \"%s%%\" LIMIT %s" % (word,limit))                                                             
    rows = cursor.fetchall()
    return rows

def fuzzy(word,limit):
    cursor.execute("SELECT word FROM spell WHERE word MATCH \"%s\" LIMIT %s" % (word,limit))                                                             
    rows = cursor.fetchall()
    return rows

def autofuzzy(word,limit):
    cursor.execute("SELECT word FROM spell WHERE word MATCH \"%s*\" LIMIT %s" % (word,limit))                                                             
    rows = cursor.fetchall()
    return rows
