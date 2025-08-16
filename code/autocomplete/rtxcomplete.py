import sqlite3
import re
import timeit
import sys
import os
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

RTXConfig = RTXConfiguration()
autocomplete_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'autocomplete'])


conn = None
cursor = None
cache_conn = None
cache_cursor = None


def load():
    global conn
    global cursor
    global cache_conn
    global cache_cursor
    database_name = f"{autocomplete_filepath}{os.path.sep}{RTXConfig.autocomplete_path.split('/')[-1]}"
    conn = sqlite3.connect(f"file:{database_name}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    cursor = conn.cursor()
    try:
        conn.execute(f"SELECT term FROM terms LIMIT 1")
        print(f"INFO: Connected to {database_name}",file=sys.stderr)
    except:
        print(f"WARN: Could NOT connect to {database_name}. Please check that file and database exist!",file=sys.stderr)

    cache_database_name = os.path.dirname(os.path.abspath(__file__)) + '/rtxcomplete_cache.sqlite'
    cache_conn = sqlite3.connect(cache_database_name)
    cache_cursor = cache_conn.cursor()
    print(f"INFO: Connected to {cache_database_name}",file=sys.stderr)
    cache_cursor.execute("CREATE TABLE IF NOT EXISTS cached_fragments(fragment VARCHAR(1024))")
    cache_cursor.execute("CREATE TABLE IF NOT EXISTS cached_fragment_terms(fragment_id VARCHAR(1024), term VARCHAR(1024))")

    return True


def get_nodes_like(word,requested_limit):

    debug = True

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
        eprint(f"INFO: Query 1")
    #cursor.execute("SELECT term FROM term WHERE term LIKE \"%s%%\" ORDER BY length(term),term LIMIT %s" % (word,1000))
    cursor.execute(f"SELECT term FROM terms WHERE term > \"{floor}\" AND term < \"{ceiling}\" AND term LIKE \"{word}%%\" ORDER BY length(term),term LIMIT {requested_limit}")
    rows = cursor.fetchall()
    values_dict = {}
    for row in rows:
        term = row[0]
        if term.upper() not in values_dict:
            if debug:
                eprint(f"    - {term}")
            properties = { "curie": '??', "name": term, "type": '??' }
            values.append(properties)
            values_dict[term.upper()] = 1
            n_values += 1
            if n_values >= requested_limit:
                break
    t1 = timeit.default_timer()
    if debug:
        eprint(f"INFO: Query 1 in {t1-t0} sec")

    #### If we haven't reached the limit yet, add a list of matching terms that contain this string
    if n_values < requested_limit:
        if debug:
            eprint(f"INFO: Query 2")

        #### See if there is a cached entry already
        word_part = word
        found_fragment = None
        while len(word_part) > 2:
            cache_cursor.execute(f"SELECT rowid, fragment FROM cached_fragments WHERE fragment == \"{word_part}\"")
            rows = cache_cursor.fetchall()
            if len(rows) > 0:
                fragment_id = rows[0][0]
                found_fragment = rows[0][1]
                break
            word_part = word_part[:-1]

        if found_fragment:
            if debug:
                eprint(f"Found matching fragment {found_fragment} as fragment_id {fragment_id}")

            cache_cursor.execute(f"SELECT term FROM cached_fragment_terms WHERE fragment_id = {fragment_id} AND term LIKE \"%%{word}%%\"")
            rows = cache_cursor.fetchall()

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
                cache_cursor.execute("INSERT INTO cached_fragments(fragment) VALUES(?)", (word,))
                fragment_id = cache_cursor.lastrowid
            except:
                eprint(f"ERROR: Unable to INSERT into cached_fragments(fragment)",file=sys.stderr)
                fragment_id = 0
            if debug:
                eprint(f"fragment_id = {fragment_id}")

            #### Execute an expensive LIKE query
            cursor.execute("SELECT term FROM terms WHERE term LIKE \"%%%s%%\" ORDER BY length(term),term LIMIT %s" % (word,10000))
            rows = cursor.fetchall()

            for row in rows:
                term = row[0]
                if term.upper() not in values_dict:

                    if n_values < requested_limit:
                        if debug:
                            eprint(f"    - {term}")
                        properties = { "curie": '??', "name": term, "type": '??' }
                        values.append(properties)
                        n_values += 1

                    values_dict[term.upper()] = 1
                    cache_cursor.execute("INSERT INTO cached_fragment_terms(fragment_id, term) VALUES(?,?)", (fragment_id, term,))
            cache_conn.commit()

        t2 = timeit.default_timer()
        if debug:
            eprint(f"INFO: Query 2 in {t2-t1} sec")


    return(values)

