import sqlite3
import re

conn = None
cursor = None

def load():
    global conn
    global cursor
    conn = sqlite3.connect('dict.db')
    conn.enable_load_extension(True)

    #### Comment out on Windows because I don't have it installed
    conn.load_extension("./spellfix")

    cursor = conn.cursor()
    return True

def prefix(word,limit):
    #cursor.execute("SELECT str FROM dict WHERE str LIKE \"%s%%\" ORDER BY rank DESC, length(str)  LIMIT %s" % (word,limit))
    #rows = cursor.fetchall()
    #rows = [ "%s" % x for x in rows]
    #if len(rows) == 0:
    word = word.strip()
    if word[-1] == '?':
        word = word[:-1]
    cursor.execute("SELECT str FROM questions WHERE str LIKE \"%%%s%%\" ORDER BY rank DESC, length(str)" % (word))
    rows = cursor.fetchall()
    try:
        if len(rows) > int(limit):
            rows = rows[:int(limit)]
    except:
        pass
    if len(rows) > 0:
        rows = [ "%s" % x for x in rows]
        results = [] #strip $variables from returns
        for item in rows:
            temp = re.sub(r'\$[a-zA-Z0-9]+', '',item)
            results.append(temp)
        return results
    #print "found no matching direct query, looking for terms"
    terms = word.split(" ")
    idx = len(terms)-1
    while idx > 0:
        temp = " ".join(terms[:idx])
        #print "checking '" + temp + "'"
        cursor.execute("SELECT str FROM questions WHERE str LIKE \"%%%s%%\" ORDER BY rank DESC, length(str)" % (temp))
        rows = cursor.fetchall()
        rows = [ "%s" % x for x in rows]
        # does not handle if there are two questions with the same
        # wording, but different variables
        #print rows
        rows = [item for item in rows if "$" in item]
        #print rows
        if len(rows) > 0:
            #print len(rows)
            
            #print rows
            temp = rows[0].split(" ")
            #print "found a match"
            #print temp
            #this relies on the variable being the last token in Q
            if temp[-1][0] ==  "$":
                #print "last was variable"
                table = temp[-1][1:]
                newWord = " ".join(terms[len(temp)-1:])
                #print terms
                #print "newWord is '" + newWord + "'"
                potential = get_alt_table_suggs(table,newWord,limit)
                retval = []
                query = " ".join(temp[:-1])
                #print "first part is '" + query + "'"
                #print "potential is"
                #print potential
                for item in potential:
                    retval.append(query+" "+item)
                return retval
            else:
                #print "last word was not variable"
                idx -= 1
        else:
            #print "no match"
            idx -= 1
    #no matches as to question templates
    print("no query or template matches")
    print("looking for variable fits")
    term_type, full_term = get_term_type(word)
    if term_type is not None:
        print("found term is variable")
        print(term_type)
        print(full_term)
        cursor.execute("SELECT str FROM questions WHERE str LIKE \"%%%s%%\" ORDER BY rank DESC, length(str)" % ("$"+term_type))
        rows = cursor.fetchall()
        rows = [ "%s" % x for x in rows]
        if len(rows) > int(limit):
            rows = rows[:int(limit)]
        print("found questions")
        print(rows)
        results = []
        for item in rows:
            temp = re.sub(r'\$[a-zA-Z_]+',full_term,item)
            results.append(temp)
        print("replaced term")
        print(results)
        return results
    return []

def get_term_type(term):
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()
        table_names = [ "%s" % x for x in table_names]
        for table in table_names:
            cursor.execute("SELECT str FROM %s WHERE str LIKE \"%s\" ORDER BY length(str)" % (table,term))
            matches = cursor.fetchall()
            matches = [ "%s" % x for x in matches]
            if len(matches) > 0:
                return table, matches[0]
    except:
        pass
    return None, None
    
def get_alt_table_suggs(table,word,limit):
    try:
        cursor.execute("SELECT str FROM %s WHERE str LIKE \"%s%%\" ORDER BY length(str)" % (table,word))
        rows = cursor.fetchall()
        if len(rows) > int(limit):
            rows = rows[:int(limit)]
    except:
        return []
    if len(rows) > 0:
        rows = [ "%s" % x for x in rows]
    return rows


def fuzzy(word,limit):
    cursor.execute("SELECT word FROM spell WHERE word MATCH \"%s\" LIMIT %s" % (word,limit))
    #cursor.execute("SELECT word FROM spell WHERE word MATCH \"%s*\" AND TOP=%s" % (word,limit))
    rows = cursor.fetchall()
    return rows


def get_nodes_like(word,limit):
    #### Get a list of matching node names that begin with these letters
    cursor.execute("SELECT curie,name,type FROM node WHERE name LIKE \"%s%%\" ORDER BY length(name),name LIMIT %s" % (word,limit))
    rows = cursor.fetchall()
    values = list()
    values_dict = dict()
    for row in rows:
        curie,name,type = row
        if name not in values_dict:
            properties = { "curie": curie, "name": name, "type": type }
            values.append(properties)
            values_dict[name] = 1
    n_values = len(values)
    limit = int(limit)

    #### If we haven't reached the limit yet, add a list of matching node names that contain this string
    if n_values < limit:
        cursor.execute("SELECT curie,name,type FROM node WHERE name LIKE \"%%%s%%\" ORDER BY length(name),name LIMIT %s" % (word,limit-n_values))
        rows = cursor.fetchall()
        for row in rows:
            curie,name,type = row
            if name not in values_dict:
                properties = { "curie": curie, "name": name, "type": type }
                values.append(properties)
                values_dict[name] = 1

    #### If we haven't reached the limit yet, add a list of matching node curies that contain this string
    if n_values < limit:
        cursor.execute("SELECT curie,name,type FROM node WHERE curie LIKE \"%%%s%%\" ORDER BY length(name),name LIMIT %s" % (word,limit-n_values))
        rows = cursor.fetchall()
        for row in rows:
            curie,name,type = row
            if name not in values_dict:
                properties = { "curie": curie, "name": name, "type": type }
                values.append(properties)
                values_dict[name] = 1

    return(values)


def get_tables():
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    rows = cursor.fetchall()
    return rows


def autofuzzy(word,limit):
    cursor.execute("SELECT word FROM spell WHERE word MATCH \"%s*\" LIMIT %s" % (word,limit))                                                             
    rows = cursor.fetchall()
    return rows
