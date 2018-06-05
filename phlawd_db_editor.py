import sys
import argparse as ap
import sqlite3

# convienience for printing to sys err
def pse(toprint):
    print >> sys.stderr,toprint


def get_next_id(conn):
    c = conn.cursor()
    sql = "select * from phlawd_db_editor_newids order by rowid desc limit 1"
    c.execute(sql)
    l = c.fetchall()
    nid = None
    for i in l:
        nid = str(i[1])
    return nid

def rebuild(conn):
    # do the left and right values
    return

def create_necessary_table(conn):
    # first check to see if it exists
    c = conn.cursor()
    created = False
    sql = "select name from sqlite_master where type = 'table' and name = 'phlawd_db_editor_newids'"
    c.execute(sql)
    l = c.fetchall()
    for i in l:
        created = True
    # if not, create
    if created == False:
        sql = "create table phlawd_db_editor_newids (id INTEGER PRIMARY KEY, ncbi_id INTEGER)"
        c.execute(sql)
        conn.commit()
        sql = "insert into phlawd_db_editor_newids (ncbi_id) values (66600001)"
        c.execute(sql)
        conn.commit()
    return

def create(args,conn):
    c = conn.cursor()
    # get the parent first
    pse("getting the parent "+args[1])
    c.execute("select * from taxonomy where ncbi_id = ? and name_class = 'scientific name'",(args[1],))
    l = c.fetchall()
    for i in l:
        id = str(i[1])
        nm = str(i[2])
        rk = str(i[4])
        pid = str(i[5])
        pse("id,name,parent_id,rank")
        pse(id+","+nm+","+pid+","+rk)
    # just create the taxon name
    gnid = get_next_id(conn)
    pse("adding "+args[0]+"("+gnid+") to be a child of "+args[1])    
    sql = "insert into taxonomy (name,name_class,parent_ncbi_id,ncbi_id,edited_name) values ('"+args[0]+"','scientific name',"+str(args[1])+","+gnid+",'"+args[0]+"')"
    pse(sql)
    c.execute(sql)
    x = c.lastrowid
    conn.commit()
    #increment new ids
    gnidp1 = str(int(gnid)+1)
    sql = "insert into phlawd_db_editor_newids (ncbi_id) values ("+gnidp1+")"
    c.execute(sql)
    conn.commit()
    pse(x)
    return

def delete(args,conn):
    # do the taxon
    c = conn.cursor()
    pse("deleting "+str(args[0]))
    sql = "delete from taxonomy where ncbi_id="+str(args[0])
    pse(sql)
    c.execute(sql)
    conn.commit()
    return

def move(args,conn):
    # do the name
    c = conn.cursor()
    sql = "update taxonomy set parent_ncbi_id = "+str(args[1])+" where ncbi_id = "+str(args[0])
    pse(sql)
    c.execute(sql)
    conn.commit()
    return

def rename(args,conn):
    # do the name
    c = conn.cursor()
    sql = "update taxonomy set name = '"+str(args[1])+"', edited_name = '"+str(args[1])+"' where ncbi_id = "+str(args[0])
    pse(sql)
    c.execute(sql)
    conn.commit()
    return

def info(args,conn):
    idin = True
    try:
        int(args[0])
    except:
        idin = False
    c = conn.cursor()
    if idin == True:
        c.execute("select * from taxonomy where ncbi_id = ? and name_class = 'scientific name'",(args[0],))
    else:
        c.execute("select * from taxonomy where name like '"+args[0]+"' and name_class = 'scientific name'",)
    l = c.fetchall()
    for i in l:
        id = str(i[1])
        nm = str(i[2])
        rk = str(i[4])
        pid = str(i[5])
        pse("id,name,parent_id,rank")
        pse(id+","+nm+","+pid+","+rk)


def generate_argparser():
    parser = ap.ArgumentParser(prog="phlawd_db_editor.py",
        formatter_class=ap.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c","--create",type=str,nargs=2,required=False,
        help=("Create a taxon (requires PARENTID and NEWID)."),metavar=("NAME","PARENTID"))
    parser.add_argument("-d","--delete",type=int,nargs=1,required=False,
        help=("Delete an id. If there are subtending taxa, it will break and \
            you will need to use -f option along with -d"),metavar=("ID"))
    parser.add_argument("-m","--move",type=int,nargs=2,required=False,
        help=("Move ncbi id1 to be a child of id2 like -m id1 id2"),metavar=("ID1","ID2"))
    parser.add_argument("-r","--rename",type=str,nargs=2,required=False,
        help=("Rename id to name like -r id name."),metavar=("ID","NAME"))
    parser.add_argument("-f","--force",action='store_true',default=False,required=False,
        help=("Force. This can be used with -d to delete despite subtending taxa."))
    parser.add_argument("-b","--database",type=str,nargs=1,required=True,
        help=("Location of database. MAKE A COPY BEFORE EDITING!"))
    parser.add_argument("-i","--info",type=str,nargs=1,required=False,
        help=("Get information about an id or taxon."),metavar=("ID/NAME"))
    parser.add_argument("--rebuild",action="store_true",help=("Once you are all done,\
        you need to do this so that the left and right values are correct."))
    return parser

def main():
    parser = generate_argparser()
    if len(sys.argv[1:]) == 0:
        sys.argv.append("-h")
    args = parser.parse_args(sys.argv[1:])
    operation = None # will be C, D, M, R, I,B
    operations = 0
    if args.create:
        operation = 'C'
        operations += 1
    if args.delete:
        operation = 'D'
        operations += 1
    if args.move:
        operation = 'M'
        operations += 1
    if args.rename:
        operation = 'R'
        operations += 1
    if args.info:
        operation = 'I'
        operations += 1
    if args.rebuild == True:
        operation = 'B'
        operations += 1
    if operations > 1:
        pse("You have chosen to do multiple operations. You can only do one at a time. Exiting...")
        sys.exit(0)
    
    dbloc = args.database[0]
    pse("connecting to "+dbloc)
    conn = sqlite3.connect(dbloc)
    create_necessary_table(conn)
    if operation == 'C':
        create(args.create,conn)
    elif operation == 'D':
        delete(args.delete,conn)
    elif operation == 'M':
        move(args.move,conn)
    elif operation == 'R':
        rename(args.rename,conn)
    elif operation == 'I':
        info(args.info,conn)
    pse("closing "+dbloc)
    conn.close()
    return

if __name__ == "__main__":
    main()