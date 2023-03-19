import pymysql, re

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from flaskext.mysql import MySQL

app = Flask(__name__)
app.secret_key = 'buu-iot'

mysql = MySQL()

#MySQL Configuration
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_DB'] = 'iot_project'
mysql.init_app(app)

# -------------------------- Content --------------------------

# @app.route("/home")
# def Index():
#     db = mysql.connect()
#     cursor = db.cursor(pymysql.cursors.DictCursor)
#     # Check if user is logged in
#     if 'loggedin' in session:
#         cursor.execute("SELECT * FROM course INNER JOIN session ON session.course_id=course.course_id")
#         data = cursor.fetchone()
#         print(data)
#         # if user logged in show them homepage
#         return render_template('index.html', student_id=session['student_id'], student_name=session['name'], data=data)
#     # if user isn't logged in return to login page
#     return redirect(url_for('Login'))

@app.route("/register_std", methods=['GET', 'POST'])
def Register_std():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    msg = ''

    # if username & password POST request exist
    if request.method == "POST" and 'pw' in request.form and 'conf_pw' in request.form and 'student_id' in request.form and 'username' in request.form:
        # Create variable for easy access
        student_id = request.form['student_id']
        username = request.form['username']
        password = request.form['pw']
        conf_pw = request.form['conf_pw']
        name = request.form['name']

        print(student_id, username, password, name)

        # Check if account exist in MySQL
        cursor.execute("SELECT * from student WHERE std_id = %s", (student_id,))
        # Fetch one record
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists'
        elif not student_id or not username or not name or not password:
            msg = 'Please fill out the form'
        elif not re.match(r'[0-9]+', student_id):
            msg = 'Invalid student id'
        elif not password == conf_pw:
            msg = 'Password did not match'
        else:
            # Account does not exist
            cursor.execute("INSERT INTO student (std_id, std_name, password, conf_password, username) VALUES (%s, %s, %s, %s, %s)", (student_id, name, password, conf_pw, username))
            db.commit()
            msg = 'Successfully Registered'

    elif request.method == "POST":
        msg = 'Please fill out the form'

    return render_template("register_std.html", msg=msg)

@app.route("/register_teacher", methods=['GET', 'POST'])
def Register_teacher():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    msg = ''

    # if username & password POST request exist
    if request.method == "POST" and 'pw' in request.form and 'conf_pw' in request.form and 'username' in request.form:
        # Create variable for easy access
        username = request.form['username']
        password = request.form['pw']
        conf_pw = request.form['conf_pw']
        name = request.form['name']

        print(username, password, name)

        # Check if account exist in MySQL
        cursor.execute("SELECT * from student WHERE std_id = %s", (username,))
        # Fetch one record
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists'
        elif not username or not name or not password:
            msg = 'Please fill out the form'
        elif not password == conf_pw:
            msg = 'Password did not match'
        else:
            # Account does not exist
            cursor.execute("INSERT INTO teacher (teacher_name, username, password, conf_password) VALUES (%s, %s, %s, %s)", (name, username, password, conf_pw))
            db.commit()
            msg = 'Successfully Registered'

    elif request.method == "POST":
        msg = 'Please fill out the form'

    return render_template("register_teacher.html", msg=msg)

@app.route("/", methods=['GET', 'POST'])
def Login():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    msg = ''

    # If "username" and "password" POST requests exist (user submitted form)
    if request.method == "POST" and 'username' in request.form and 'pw' in request.form :
        # Create variable
        username = request.form['username']
        pw = request.form['pw']
        # Check if accounts exist in MySQL
        cursor.execute("SELECT * FROM student WHERE username = %s AND password = %s", (username, pw))
        # Fetch one record
        std = cursor.fetchone()
        cursor.execute("SELECT * FROM teacher WHERE username = %s AND password = %s", (username, pw))
        teacher = cursor.fetchone()

        if std:
            # Create session data to access in other route
            session['loggedin'] = True
            session['std'] = True
            session['std_id'] = std['std_id']
            session['std_name'] = std['std_name']
            # Redirect to index page
            # return redirect((url_for('Index')))
        elif teacher:
            # Create session data to access in other route
            session['loggedin'] = True
            session['teacher'] = True
            session['teacher_id'] = teacher['teacher_id']
            session['username'] = teacher['username']
            session['teacher_name'] = teacher['teacher_name']
            # Redirect to index page
            return redirect((url_for('THome')))
        else:
            msg = 'Incorrect student id or password'

    return render_template("login.html", msg=msg)

# ---------------- teacher section ---------------- #

@app.route("/teacher/home")
def THome():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    if 'loggedin' in session and 'teacher' in session:
        cursor.execute("SELECT * from subject")
        subject = cursor.fetchall()
        return render_template("/teacher/index.html", teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'], subject=subject)
    return redirect(url_for(Login))

@app.route("/teacher/edit/<id>", methods=['GET','POST'])
def GetUser(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM teacher WHERE teacher_id = %s", (id))
    data = cursor.fetchall()
    print(data[0])
    return render_template("/teacher/edit.html", user=data[0])
    
@app.route("/teacher/update/<id>", methods=['POST'])
def Update(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    msg = ''

    if request.method == 'POST' and 'username' in request.form and 'teacher_name' in request.form:
        name = request.form['teacher_name']
        username = request.form['username']
        cursor.execute("\
                    UPDATE teacher\
                    SET teacher_name = %s,\
                        username = %s\
                    WHERE teacher_id = %s\
                    ", (name, username, id))
        db.commit()
        return redirect(url_for('Login'))
    elif request.method == 'POST' and 'password' in request.form and 'conf_pw' in request.form:
        password = request.form['password']
        conf_pw = request.form['conf_pw']

        if password == conf_pw:
            cursor.execute("\
                        UPDATE teacher\
                        SET password = %s,\
                            conf_password = %s\
                        WHERE teacher_id = %s\
                        ", (password, conf_pw, id))
            db.commit()
            return redirect(url_for('Login'))
        else:
            msg = 'Password did not match'
            return render_template("/teacher/edit.html", msg=msg)
     
# start app
if __name__ == "__main__":
    app.run(port=4000, debug=True)