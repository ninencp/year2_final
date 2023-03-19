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
            session['std_id'] = std['std_id']
            session['name'] = std['std_name']
            # Redirect to index page
            # return redirect((url_for('Index')))
        elif teacher:
            # Create session data to access in other route
            session['loggedin'] = True
            session['username'] = teacher['username']
            session['name'] = teacher['teacher_name']
            # Redirect to index page
            # return redirect((url_for('Index')))
        else:
            msg = 'Incorrect student id or password'

    return render_template("login.html", msg=msg)

# ---------------- teacher section ---------------- #

# @app.route("/teacher/home")

# start app
if __name__ == "__main__":
    app.run(port=4000, debug=True)