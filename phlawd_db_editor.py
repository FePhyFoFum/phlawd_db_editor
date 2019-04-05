import sys
import argparse as ap
import sqlite3
from time import strftime,gmtime
import datetime

import seq

# logfile and count that we will use globally
logfile = None
count = 1

# convienience for printing to sys err
def pse(toprint):
    print >> sys.stderr,toprint

def log(toprint):
    global logfile
    stt = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    logfile.write(stt+" || "+toprint+"\n")

def get_next_id(conn):
    c = conn.cursor()
    sql = "select * from phlawd_db_editor_newids order by rowid desc limit 1"
    c.execute(sql)
    l = c.fetchall()
    nid = None
    for i in l:
        nid = str(i[1])
    return nid

# this takes a start id, and start left which should be 1, 1 and then will be recursive
def rebuild(gid, lft, cursor,conn):
    global count
    # do the left and right values
    rgt = lft + 1
    sql = "select ncbi_id from taxonomy where parent_ncbi_id = "+str(gid)
    cursor.execute(sql)
    l = cursor.fetchall()
    res = set()
    for i in l:
        if str(i[0]) != gid:
            res.add(str(i[0]))
    for i in res:
        rgt = rebuild(i,rgt,cursor,conn)
    updcmd = "update taxonomy set left_value = "+str(lft)+", right_value = "+str(rgt)+" where ncbi_id = "+str(gid)+";"
    #pse(updcmd)
    cursor.execute(updcmd)
    if count % 100000 == 0:
        pse(count)
        #sys.exit(0)
        conn.commit()
    count += 1
    return rgt + 1

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
        log("creating the phlawd_db_editor_newids table with start value 66600001")
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
        #pse("id,name,parent_id,rank")
        #pse(id+","+nm+","+pid+","+rk)
    # just create the taxon name
    gnid = get_next_id(conn)
    pse("creating "+args[0]+"("+gnid+") to be a child of "+args[1])
    log("creating "+args[0]+"("+gnid+") to be a child of "+args[1])
    sql = "insert into taxonomy (name,name_class,parent_ncbi_id,ncbi_id,edited_name,node_rank) values ('"+args[0]+"','scientific name',"+str(args[1])+","+gnid+",'"+args[0]+"','"+str(args[2])+"')"
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

def addseqs(args,conn):
    pse("opening "+args[0]+" to add sequences")
    log("opening "+args[0]+" to add sequences")
    c = conn.cursor()
    count = 0
    for i in seq.read_fasta_file_iter(args[0]):
        spls = i.name.split("@")
        ncbiid = spls[0]
        seqid = spls[1]
        pse("adding "+seqid+" ("+ncbiid+") ")
        log("adding "+seqid+" ("+ncbiid+") ")
        sql = "insert into sequence (ncbi_id,accession_id,locus,version_id,title,description,seq) values ('"+ncbiid+"','"+seqid+"','"+seqid+"','"+seqid+".1', 'sequence added on "+str(datetime.datetime.now())+"','sequence added on "+str(datetime.datetime.now())+"','"+i.seq+"')"
        c.execute(sql)
        conn.commit()
        count += 1
    pse("added "+str(count)+" new sequences")
    log("added "+str(count)+" new sequences")
    return

def get_all_subtending_ids(inid,conn):
    c = conn.cursor()
    sql = "select left_value,right_value from taxonomy where name_class = 'scientific name' and ncbi_id ="+str(inid)
    c.execute(sql)
    l = c.fetchall()
    lf = ""
    rt = ""
    for i in l:
        lf = str(i[0])
        rt = str(i[1])
    ids = []
    if lf != "" and rt != "":
        sql = "select ncbi_id from taxonomy where left_value >= "+lf+" and right_value <= "+rt
        c.execute(sql)
        l = c.fetchall()
        for i in l:
            ids.append(str(i[0]))
    return ids

def delete(args,conn):
    # do the taxon
    c = conn.cursor()
    # get all the subtending ids
    ids = get_all_subtending_ids(args[0],conn)
    # do the seqs
    pse("deleting seqs associated with "+str(args[0]) +" (recursively)")
    log("deleting seqs associated with "+str(args[0]) +" (recursively)")
    for i in ids:
        sql = "delete from sequence where ncbi_id = "+str(i)
        c.execute(sql)
    pse("deleting "+str(args[0]) +" (recursively)")
    log("deleting "+str(args[0]) +" (recursively)")
    for i in ids:
        sql = "delete from taxonomy where ncbi_id = "+str(i)
        c.execute(sql)
    pse("vacuuming")
    log("vacuuming")
    c.execute("vacuum")
    conn.commit()
    return

def move(args,conn):
    # do the name
    c = conn.cursor()
    pse("moving "+str(args[0])+" to be a child of "+str(args[1]))
    log("moving "+str(args[0])+" to be a child of "+str(args[1]))
    sql = "update taxonomy set parent_ncbi_id = "+str(args[1])+" where ncbi_id = "+str(args[0])
    #pse(sql)
    c.execute(sql)
    conn.commit()
    return

def rename(args,conn):
    # do the name
    c = conn.cursor()
    pse("renaming "+str(args[0])+" to be "+str(args[1]))
    log("renaming "+str(args[0])+" to be "+str(args[1]))
    sql = "update taxonomy set name = '"+str(args[1])+"', edited_name = '"+str(args[1])+"' where ncbi_id = "+str(args[0])
    #pse(sql)
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
    parser.add_argument("-c","--create",type=str,nargs=3,required=False,
        help=("Create a taxon (requires NEWNAME, PARENTID, and RANK)."),metavar=("NAME","PARENTID", "RANK"))
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
    parser.add_argument("-a","--addseqs",type=str,nargs=1,required=False,
        help=("Add sequences from fasta file to existing taxa where fasta labels are >NCBITAXONIN@SEQID"))
    parser.add_argument("--rebuild",action="store_true",help=("Once you are all done,\
        you need to do this so that the left and right values are correct."))
    parser.add_argument("-l","--logfile",nargs=1,type=str,default="phlawd_db_editor.log",
        help=("Logfile for storing all commands and results."))
    return parser

def main():
    global logfile
    parser = generate_argparser()
    if len(sys.argv[1:]) == 0:
        sys.argv.append("-h")
    args = parser.parse_args(sys.argv[1:])
    pse("opening logfile "+args.logfile)
    logfile = open(args.logfile,"a")
    operation = None # will be C, D, M, R, I, B, A
    operations = 0
    if args.create:
        operation = 'C'
        operations += 1
    if args.addseqs:
        operation = 'A'
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
    elif operation == 'A':
        addseqs(args.addseqs,conn)
    elif operation == 'B':
        log("rebuilding left and right values")
        pse("rebuilding left and right values")
        cursor = conn.cursor()
        rebuild(1,1,cursor,conn)
    pse("closing "+dbloc)
    conn.close()
    logfile.close()
    return

if __name__ == "__main__":
    main()
