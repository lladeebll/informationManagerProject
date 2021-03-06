import psycopg2
import click 
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
import datetime

def getDb():
    if 'db' not in g:
        db = current_app.config['DB_NAME']
        g.db = psycopg2.connect(f"dbname={db}", sslmode='require')

    return g.db


def closeDb(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def uniqueId(id):
    
    db = getDb()
    cur = db.cursor()
    cur.execute("select username from users where username = %s",(id,))

    if(cur.fetchone() == None):
        return True
    
    else:
        return False

def insert(d, opt, user):
    
    db = getDb()
    cur = db.cursor()

    if opt == 1:
        userId = d.get('userName')
        name = d.get('firstName')
        password = d.get('password1')
        hashedPass = generate_password_hash(password, method='sha256')

        cur.execute("INSERT INTO users (username, name, password) VALUES (%s,%s,%s) ", (userId, name, hashedPass[7:]))
        db.commit()
        cur.execute("SELECT id FROM users WHERE username = %s", (userId,))
        return cur.fetchone()
    
    else:
        notes = d.get('note')
        title = d.get('title')
        cur.execute("INSERT INTO notes (title, note, addedon, stared, usr) VALUES (%s, %s, %s, %s, %s)", (title, notes, datetime.datetime.now(), False, user))
        cur.execute("SELECT * FROM tags")
        tags = cur.fetchall()
        cur.execute("SELECT id FROM notes WHERE note = %s",(notes,))
        noteId = cur.fetchone()[0]
        if opt == 2:
            t = [ item.lower() for item in d if item != 'note' and item != 'title']
        elif opt == 3:
            t = [tg.lower() for tg in d.get('tags')]
        
        for item in list(set(t)):
            needToAdd = True
            for tag in tags:
                if tag[1] == item:
                    cur.execute("INSERT INTO notetags (note, tag) VALUES (%s,%s)",(noteId,tag[0]))
                    needToAdd = False
                    break

            if needToAdd:
                cur.execute("INSERT INTO tags (tag) VALUES (%s)", (item,))
                cur.execute("INSERT INTO notetags (note, tag) VALUES (%s,(SELECT id FROM tags where tag = %s))",(noteId,item))
            

        db.commit()   
        
        
def allNotes(id):

    db = getDb()
    cur = db.cursor()

    cur.execute("SELECT ROW_NUMBER() OVER (ORDER BY n.Id) AS Sno, n.id, n.title, n.stared FROM notes n, users u WHERE n.usr = %s AND u.id = %s", (id,id))

    return cur.fetchall()

def filterbyTag(tag, id):
    db = getDb()
    cur = db.cursor()

    cur.execute("SELECT ROW_NUMBER() OVER (ORDER BY n.Id) AS Sno, n.id, n.title, n.stared FROM notes n, users u, tags t, notetags nt WHERE n.usr = %s AND u.id = n.usr AND t.tag = %s AND t.id = nt.tag AND n.id = nt.note", (id, tag))
    return cur.fetchall()

def getAllTags(id):
    db = getDb()
    cur = db.cursor()

    cur.execute("SELECT DISTINCT t.id, t.tag FROM tags t, users u, notes n, notetags nt WHERE u.id = n.usr AND u.id = %s AND t.id = nt.tag AND n.id = nt.note",(id,))
    return cur.fetchall()

def getContents(id):

    db = getDb()
    cur = db.cursor()

    d = {}
    cur.execute("SELECT title, note, addedon, stared, id FROM notes WHERE id = %s", (id,))
    d['note'] = cur.fetchone()
    cur.execute("SELECT t.tag FROM tags t, notes n, notetags nt WHERE n.id = %s AND n.id = nt.note AND t.id = nt.tag", (id,))
    d['tags'] = cur.fetchall()
    return d

def updateNote(newTitle, newNote, star, id, t = []):
    db = getDb()
    cur = db.cursor()
    cur.execute("UPDATE notes SET title = %s, note = %s, addedOn = %s, stared = %s WHERE id = %s", (newTitle, newNote, datetime.datetime.now(), star, id))
    cur.execute("DELETE FROM notetags WHERE note = %s", (int(id),))
    cur.execute("SELECT * FROM tags")
    tags = cur.fetchall()
    for item in list(set(t)):
        needToAdd = True
        for tag in tags:
            if tag[1] == item:
                cur.execute("INSERT INTO notetags (note, tag) VALUES (%s,%s)",(int(id),tag[0]))
                needToAdd = False
                break

        if needToAdd:
                cur.execute("INSERT INTO tags (tag) VALUES (%s)", (item.lower(),))
                cur.execute("INSERT INTO notetags (note, tag) VALUES (%s,(SELECT id FROM tags where tag = %s))",(int(id),item.lower()))
    

    db.commit()

def logIn(userId):

    db = getDb()
    cur = db.cursor()

    cur.execute("SELECT * FROM users where username = %s",(userId,))
    usr = cur.fetchone()

    if not usr or len(usr) == 0:
        return None

    else:
        return usr

def delete(id, uid, opt):
    db = getDb()
    cur = db.cursor()
    if opt == 1:
        cur.execute("SELECT n.id FROM notes n, users u WHERE n.usr = u.id AND u.id = %s AND n.id = %s", (uid, id))
        nid = cur.fetchone()
        if nid:
            cur.execute("DELETE FROM notetags WHERE note = %s", nid)
            cur.execute("DELETE FROM notes WHERE id = %s", nid)
            db.commit()
            pass



def initDb():

    db = getDb()
    cur = db.cursor()
    f = current_app.open_resource("SQL/tables.sql")
    sqlCode = f.read().decode("utf-8")
    cur.execute(sqlCode)
    cur.close()
    db.commit()
    closeDb()

@click.command('initdb', help="initialise the database") 
@with_appcontext
def addCommand():
    initDb()
    click.echo('Data Base Initialised')

def init_app(app):
    app.teardown_appcontext(closeDb)
    app.cli.add_command(addCommand)




    