import glob
import os
import re
import sqlite3
import sys

CONFIG_DEBUG = False

UNKNOWN_FILE = "__UNK__"
RE_RTL_FUNC = re.compile(r"^;; Function ([\w\.]+)")
RE_REF = re.compile(r"^.*\(symbol_ref:SI.*<(\S+)\s+\S+\s+([^>]+)")


def debug(s):
    if CONFIG_DEBUG:
        print("debug: %s" % s)


def warning(s):
    print("warning: %s" % s)


def get_lines(filename):
    encodings = ["utf-8", "iso-8859-1", "ascii"]
    for encoding in encodings:
        with open(filename, encoding=encoding, mode="r") as f:
            try:
                return f.readlines()
            except UnicodeDecodeError:
                # failed to decode, try some other decoding
                pass
    return []


def parse_rtl(filename):
    calls = {}
    functions = []
    function = None
    obj = os.path.basename(filename).split(".")[0]

    for line in get_lines(filename):
        if len(line) == 1:
            continue
        line = line.rstrip()

        m = RE_RTL_FUNC.match(line)
        if m:
            function = m.group(1)
            functions.append(function)
            continue

        if not function:
            continue

        m = RE_REF.match(line)
        if m:
            if m.group(1) == "function_decl":
                if function not in calls:
                    calls[function] = set()
                calls[function].add(m.group(2))
            elif m.group(1) == "var_decl":
                continue
            else:
                warning("parse_rtl: unknown decl: %s" % m.group(1))
    return obj, functions, calls


def create_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE files(
            id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL
        )"""
    )
    cursor.execute(
        """
        CREATE TABLE functions(
            id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            fileid      INTEGER NOT NULL,
            name        TEXT NOT NULL
        )"""
    )
    cursor.execute(
        """
        CREATE TABLE calls(
            id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            callerid    INTEGER NOT NULL,
            calleeid    INTEGER NOT NULL
        )"""
    )


def add_file(cursor, name):
    cursor.execute("INSERT INTO files (name) VALUES (?)", (name,))


def add_function(cursor, fileid, name):
    cursor.execute(
        """
        INSERT INTO functions (
            fileid,
            name
        ) VALUES (?, ?)""",
        (fileid, name),
    )


def add_call(cursor, callerid, calleeid):
    cursor.execute(
        """
        INSERT INTO calls (
            callerid,
            calleeid
        ) VALUES (?, ?)""",
        (callerid, calleeid),
    )


def get_file_id(cursor, name):
    cursor.execute("SELECT id FROM files WHERE name = ?", (name,))
    return cursor.fetchone()[0]


def _get_function_id(cursor, fileid, name):
    if fileid is None:
        cursor.execute("SELECT id FROM functions WHERE name = ?", (name,))
    else:
        cursor.execute(
            """
            SELECT id
            FROM functions
            WHERE fileid = ? AND name = ?""",
            (fileid, name),
        )
    return cursor.fetchone()[0]


def get_function_id(cursor, fileid, name):
    try:
        return _get_function_id(cursor, fileid, name)
    except TypeError:
        pass

    unknown_file_id = get_file_id(cursor, UNKNOWN_FILE)
    debug("get_function_id: try to find %s in %s" % (name, UNKNOWN_FILE))
    try:
        return _get_function_id(cursor, unknown_file_id, name)
    except TypeError:
        pass

    debug("get_function_id: add %s to %s" % (name, UNKNOWN_FILE))
    add_function(cursor, unknown_file_id, name)
    try:
        return _get_function_id(cursor, unknown_file_id, name)
    except TypeError:
        print("fatal: get_function_id: could not find function %s" % name)
        sys.exit(-1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "usage:\n\t%s <database.db> <f1.c.expand> [<fn.c.expand> ...]"
            % os.path.basename(sys.argv[0])
        )
        sys.exit(-1)

    if os.path.isfile(sys.argv[1]):
        os.unlink(sys.argv[1])
    connection = sqlite3.connect(sys.argv[1])
    cursor = connection.cursor()

    create_tables(cursor)
    connection.commit()

    files = []
    for arg in sys.argv[2:]:
        for file in glob.glob(arg):
            files.append(file)
    files = sorted(files)

    cache = []
    for file in files:
        cache.append(parse_rtl(file))

    for name, _, _ in cache:
        debug("add_file(%s)" % (name))
        add_file(cursor, name)
    debug("add_file(%s)" % (name))
    add_file(cursor, UNKNOWN_FILE)
    connection.commit()

    for name, functions, _ in cache:
        fileid = get_file_id(cursor, name)
        for function in functions:
            debug("add_function(%s, %s)" % (name, function))
            add_function(cursor, fileid, function)
    connection.commit()

    for name, functions, calls in cache:
        for caller, callees in calls.items():
            localfileid = get_file_id(cursor, name)
            callerid = get_function_id(cursor, localfileid, caller)
            for callee in callees:
                if callee in functions:
                    debug("local: %s -> %s" % (caller, callee))
                    calleeid = get_function_id(cursor, localfileid, callee)
                else:
                    debug("remote: %s -> %s" % (caller, callee))
                    calleeid = get_function_id(cursor, None, callee)
                add_call(cursor, callerid, calleeid)

    connection.commit()
    connection.close()
