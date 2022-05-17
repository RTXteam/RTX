import sqlite3
import re
import timeit
import sys
import os

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

RTXConfig = RTXConfiguration()
autocomplete_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'autocomplete'])


conn = None
cursor = None


def load():
    global conn
    global cursor
    database_name = f"{autocomplete_filepath}{os.path.sep}{RTXConfig.autocomplete_path.split('/')[-1]}"
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()
    #print(f"INFO: Connected to {database_name}",file=sys.stderr)
    return True


def get_nodes_like(word,requested_limit):

    debug = False

    t0 = timeit.default_timer()
    requested_limit = int(requested_limit)

    values = []
    n_values = 0

    if len(word) < 2:
        return values

    #### Try to avoid SQL injection exploits by sanitizing input #1823
    word = word.replace('"','')

    floor = word[:-1]
    ceiling = floor + 'zz'

    #### Get a list of matching node names that begin with these letters
    if debug:
        print(f"INFO: Query 1")
    #cursor.execute("SELECT term FROM term WHERE term LIKE \"%s%%\" ORDER BY length(term),term LIMIT %s" % (word,1000))
    cursor.execute(f"SELECT term FROM terms WHERE term > \"{floor}\" AND term < \"{ceiling}\" AND term LIKE \"{word}%%\" ORDER BY length(term),term LIMIT {requested_limit}")
    rows = cursor.fetchall()
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

        #### See if there is a cached entry already
        word_part = word
        found_fragment = None
        while len(word_part) > 2:
            cursor.execute(f"SELECT rowid, fragment FROM cached_fragments WHERE fragment == \"{word_part}\"")
            rows = cursor.fetchall()
            if len(rows) > 0:
                fragment_id = rows[0][0]
                found_fragment = rows[0][1]
                break
            word_part = word_part[:-1]

        if found_fragment:
            if debug:
                print(f"Found matching fragment {found_fragment} as fragment_id {fragment_id}")

            cursor.execute(f"SELECT term FROM cached_fragment_terms WHERE fragment_id = {fragment_id} AND term LIKE \"%%{word}%%\"")
            rows = cursor.fetchall()

            for row in rows:
                term = row[0]
                if term.upper() not in values_dict:

                    if n_values < requested_limit:
                        if debug:
                            print(f"    - {term}")
                        properties = { "curie": '??', "name": term, "type": '??' }
                        values.append(properties)
                        n_values += 1


        if found_fragment is None:

            #### Cache this fragment in the database
            try:
                cursor.execute("INSERT INTO cached_fragments(fragment) VALUES(?)", (word,))
                fragment_id = cursor.lastrowid
            except:
                print(f"ERROR: Unable to INSERT into cached_fragments(fragment)",file=sys.stderr)
                fragment_id = 0
            if debug:
                print(f"fragment_id = {fragment_id}")

            #### Execute an expensive LIKE query
            cursor.execute("SELECT term FROM terms WHERE term LIKE \"%%%s%%\" ORDER BY length(term),term LIMIT %s" % (word,10000))
            rows = cursor.fetchall()

            for row in rows:
                term = row[0]
                if term.upper() not in values_dict:

                    if n_values < requested_limit:
                        if debug:
                            print(f"    - {term}")
                        properties = { "curie": '??', "name": term, "type": '??' }
                        values.append(properties)
                        n_values += 1

                    values_dict[term.upper()] = 1
                    cursor.execute("INSERT INTO cached_fragment_terms(fragment_id, term) VALUES(?,?)", (fragment_id, term,))
            conn.commit()

        t2 = timeit.default_timer()
        if debug:
            print(f"INFO: Query 2 in {t2-t1} sec")


    return(values)

