from anytree import NodeMixin, RenderTree
import iterfzf
import os
import re
import sqlite3
import sys


class Function(NodeMixin):
    def __init__(self, name, id_, parent=None, children=None):
        self.name = name
        self.id_ = id_
        self.parent = parent
        if children:
            self.children = children


def get_all_functions(cursor):
    cursor.execute(
        """
        SELECT files.name, functions.name
        FROM files, functions
        WHERE functions.fileid = files.id
        """
    )
    return ("%s (%s)" % (function, file) for (file, function) in cursor.fetchall())


def get_function_id(cursor, module, name):
    cursor.execute(
        """
        SELECT functions.id
        FROM files, functions
        WHERE
            files.id == functions.fileid AND
            files.name == ? AND
            functions.name = ?""",
        (module, name),
    )
    try:
        return cursor.fetchone()[0]
    except TypeError:
        return None


def get_function_details(cursor, functionid):
    cursor.execute(
        """
        SELECT files.name, functions.name
        FROM files, functions
        WHERE
            functions.id = ? AND
            files.id == functions.fileid""",
        (functionid,),
    )
    return cursor.fetchone()


def pretty_function(fntuple):
    return "%s (%s)" % (fntuple[1], fntuple[0])


def get_callees(cursor, functionid):
    cursor.execute(
        """
        SELECT calleeid
        FROM calls
        WHERE callerid == ?""",
        (functionid,),
    )
    return [x for (x,) in cursor.fetchall()]


def get_callers(cursor, functionid):
    cursor.execute(
        """
        SELECT callerid
        FROM calls
        WHERE calleeid == ?""",
        (functionid,),
    )
    return [x for (x,) in cursor.fetchall()]


def traverse(cursor, parent, nodes):
    for callerid in get_callers(cursor, parent.id_):
        if callerid not in nodes:
            caller = Function(
                pretty_function(get_function_details(cursor, callerid)),
                callerid,
                parent=parent,
            )
            nodes[callerid] = caller
            traverse(cursor, caller, nodes)
        else:
            # cut branch we've already seen
            empty = Function(
                pretty_function(get_function_details(cursor, callerid)),
                -1,
                parent=parent,
            )
            Function("...", -1, parent=empty)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage:\n\t%s <database.db>" % os.path.basename(sys.argv[0]))
        sys.exit(-1)

    connection = sqlite3.connect(sys.argv[1])
    cursor = connection.cursor()

    line = iterfzf.iterfzf(get_all_functions(cursor), case_sensitive=False)
    if line is None:
        sys.exit(-1)

    m = re.match(r"(\S+)\s+\(([^\)]+)", line)
    file = m.group(2)
    function = m.group(1)
    rootid = get_function_id(cursor, file, function)
    root = Function(pretty_function(get_function_details(cursor, rootid)), rootid)
    nodes = {}
    traverse(cursor, root, nodes)

    # iterfzf doesn't seem to erase the prompt, add a few lines so it is obvious
    # where the new output starts
    print("\n\n")
    for pre, _, node in RenderTree(root):
        print("%s%s" % (pre, node.name))
