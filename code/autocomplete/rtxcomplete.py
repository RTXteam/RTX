import sqlite3
import re
import timeit

conn = None
cursor = None


def load():
    global conn
    global cursor
    database_name = 'autocomplete.sqlite'
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    return True


def get_nodes_like(word,requested_limit):

    debug = False

    t0 = timeit.default_timer()
    requested_limit = int(requested_limit)

    #### Get a list of matching node names that begin with these letters
    if debug:
        print(f"INFO: Query 1")
    cursor.execute("SELECT term FROM term WHERE term LIKE \"%s%%\" ORDER BY length(term),term LIMIT %s" % (word,1000))
    rows = cursor.fetchall()
    values = []
    n_values = 0
    values_dict = {}
    for row in rows:
        term = row[0]
        if term.upper() not in values_dict:
            if debug:
                print(f"    - {term}")
            properties = { "curie": '??', "name": term, "type": '??' }
            values.append(properties)
            values_dict[term.upper()] = 1
            n_values += 1
            if n_values >= requested_limit:
                break
    t1 = timeit.default_timer()
    if debug:
        print(f"INFO: Query 1 in {t1-t0} sec")

    #### If we haven't reached the limit yet, add a list of matching terms that contain this string
    if n_values < requested_limit:
        if debug:
            print(f"INFO: Query 2")
        cursor.execute("SELECT term FROM term WHERE term LIKE \"%%%s%%\" ORDER BY length(term),term LIMIT %s" % (word,1000))
        rows = cursor.fetchall()
        for row in rows:
            term = row[0]
            if term.upper() not in values_dict:
                print(f"    - {term}")
                properties = { "curie": '??', "name": term, "type": '??' }
                values.append(properties)
                values_dict[term.upper()] = 1
                n_values += 1
                if n_values >= requested_limit:
                    break
        t2 = timeit.default_timer()
        if debug:
            print(f"INFO: Query 2 in {t2-t1} sec")


    return(values)

