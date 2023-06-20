import pymysql, re, cv2, os, shutil, time
from pathlib import Path

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from flaskext.mysql import MySQL
from datetime import date
from datetime import datetime
from datetime import timedelta
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib

import servo
import RPi.GPIO as GPIO
import pigpio
import time

import keyboard

servo_pin = 17 #BCM

app = Flask(__name__)
app.secret_key = 'buu-iot'

mysql = MySQL()

#MySQL Configuration
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '123'
app.config['MYSQL_DATABASE_HOST'] = 'localhost' 
app.config['MYSQL_DATABASE_DB'] = 'iot_project'
mysql.init_app(app) 

# -------------------------- Function -------------------------- #

### servo
pwm = pigpio.pi()
pwm.set_mode(servo_pin, pigpio.OUTPUT)
pwm.set_PWM_frequency( servo_pin, 50 )


#### Saving Date today in 2 different formats / บันทึกวันที่วันนี้ใน 2 รูปแบบที่แตกต่างกัน
datetoday = date.today().strftime("%d_%m_%y")
datetoday2 = date.today().strftime("%d-%m-%Y")

#### Initializing VideoCapture object to access WebCam / กำหนด Webcam เเละ ดึง Model 
face_detector = cv2.CascadeClassifier('static/haarcascade_frontalface_default.xml')
eye_detector = cv2.CascadeClassifier('static/haarcascade_eye_tree_eyeglasses.xml')
# cap = cv2.VideoCapture(0)

#### If these directories don't exist, create them / หากไม่มีไดเร็กทอรีเหล่านี้ ให้สร้างขึ้นใหม่ "สร้างโฟลเดอร์หน้า"
if not os.path.isdir('Attendance'):
    os.makedirs('Attendance')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
if f'Attendance-{datetoday}.csv' not in os.listdir('Attendance'):
    with open(f'Attendance/Attendance-{datetoday}.csv','w') as f:
        # f.write('ref_teacher_id, ref_s_id, ref_std_id, check_in_date, date_save')
        f.write('teacher id,subject id,student id,check in date,date')

#### get a number of total registered users / รับจำนวนผู้ใช้ที่ลงทะเบียนทั้งหมด
def totalreg():
    return len(os.listdir('static/faces'))

#### extract the face from an image / แยกใบหน้าออกจากรูปภาพ
def extract_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_points = face_detector.detectMultiScale(gray, 1.3, 5)
    return face_points

#### Identify face using ML model / ระบุใบหน้าโดยใช้โมเดล ML
def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)

#### A function which trains the model on all the faces available in faces folder / ฟังก์ชันที่ฝึกโมเดลบนใบหน้าทั้งหมดที่มีในโฟลเดอร์ใบหน้า
def train_model():
    faces = []
    labels = []
    userlist = os.listdir('static/faces')
    for user in userlist:
        for imgname in os.listdir(f'static/faces/{user}'):
            img = cv2.imread(f'static/faces/{user}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=1)
    knn.fit(faces,labels)
    joblib.dump(knn,'static/face_recognition_model.pkl')

#### Extract info from today's attendance file in attendance folder / แยกข้อมูลจากไฟล์การเข้างานของวันนี้ในโฟลเดอร์การเข้างาน
def extract_attendance():
    df = pd.read_csv(f'Attendance/Attendance-{datetoday}.csv')
    names = df['Name']
    rolls = df['Roll']
    times = df['Time']
    l = len(df)
    return names,rolls,times,l

#### Add Attendance of a specific user / เพิ่มการเข้าร่วมของผู้ใช้เฉพาะ
def add_attendance(name, s_id, checkin_date):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    username = name.split('_')[0]
    userid = name.split('_')[1]
    cursor.execute("SELECT username from student WHERE std_id = %s", (userid))
    fetch_username = cursor.fetchone()
    username = fetch_username['username']
    current_time = datetime.now()

    print('user :',username,'id :',userid,'s_id :', s_id)

    checkin_date = datetime.strptime(checkin_date, '%d-%m-%Y').date()

    cursor.execute("SELECT s.*, std.* FROM subject as s LEFT JOIN enroll as e ON s.s_id = e.ref_s_id\
                   LEFT JOIN student as std ON e.ref_std_id = std.std_id\
                   WHERE std.username = %s and s.s_id = %s and std.std_id = %s\
                   GROUP BY s.s_id", (username, s_id, userid))
    enroll_check = cursor.fetchone()
    print('enroll check:',enroll_check)

    cursor.execute("SELECT * from checkin WHERE ref_std_id = %s AND ref_s_id = %s AND check_in_date = %s", (userid, s_id, checkin_date))
    check_exist = cursor.fetchone()

    checkin_time_str = datetime.now().strftime("%H:%M:%S")
    print(checkin_time_str)
    checkin_time = datetime.strptime(checkin_time_str, "%H:%M:%S")
    print('first:',checkin_time)
    checkin_time = timedelta(hours=checkin_time.hour, minutes=checkin_time.minute, seconds=checkin_time.second)
    print('second:',checkin_time)

    if enroll_check and not check_exist:

        in_time = enroll_check['start_time']
        out_time = enroll_check['end_time']

        if checkin_time <= in_time:
            checkin_status = 1
        elif checkin_time > in_time and checkin_time < out_time:
            checkin_status = 2
        elif checkin_time > in_time and checkin_time > out_time:
            checkin_status = 0
            
        print(checkin_date)
        cursor.execute("INSERT INTO checkin (ref_teacher_id, ref_s_id, ref_std_id, check_in_status, check_in_date, date_save)\
                        VALUES (%s,%s,%s,%s,%s,%s)", (enroll_check['ref_teacher_id'], s_id, enroll_check['std_id'], checkin_status, checkin_date, current_time))
        db.commit()

    # df = pd.read_csv(f'Attendance/Attendance-{datetoday}.csv')
    # if int(userid) not in list(df['student id']):
    #     with open(f'Attendance/Attendance-{datetoday}.csv','a') as f:
    #         f.write(f'\n{teacher_id},{s_id},{std_id},{checkin_date},{current_time}')

# -------------------------- Content -------------------------- #

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
            imagefolder = 'static/faces/'+username+'_'+str(student_id)
            if not os.path.isdir(imagefolder):
                os.makedirs(imagefolder)
            cap = cv2.VideoCapture(0)
            i,j = 0,0
            while 1:
                _,frame = cap.read()
                faces = extract_faces(frame)
                for (x,y,w,h) in faces:
                    cv2.rectangle(frame,(x, y), (x+w, y+h), (255, 0, 20), 2)
                    cv2.putText(frame,f'Images Captured: {i}/100',(30,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255, 0, 20),2,cv2.LINE_AA)
                    if j%10==0:
                        filename = username+'_'+str(i)+'.jpg'
                        cv2.imwrite(imagefolder+'/'+filename,frame[y:y+h,x:x+w])
                        i+=1
                    j+=1
                if j==1000:
                    cursor.execute("INSERT INTO student (std_id, std_name, password, conf_password, username) VALUES (%s, %s, %s, %s, %s)", (student_id, name, password, conf_pw, username))
                    cursor.execute("INSERT INTO face (ref_std_id) VALUES (%s)", (student_id))
                    db.commit()
                    msg = 'Successfully Registered'
                    break
                cv2.imshow('Adding student face', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    shutil.rmtree(imagefolder)
                    break
            cap.release()
            cv2.destroyAllWindows()
            train_model()

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
            print('student')
            # Create session data to access in other route
            session['loggedin'] = True
            session['std'] = True
            session['std_id'] = std['std_id']
            session['std_name'] = std['std_name']
            session['username'] = std['username']
            # Redirect to index page
            return redirect((url_for('StdHome')))
        elif teacher:
            print('teacher')
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

@app.route("/teacher/logout")
def TLogout():
    # Remove session data. This will log user out.
    session.pop('loggedin', None)
    session.pop('teacher', None)
    session.pop('teacher_id', None)
    session.pop('teacher_name', None)
    session.pop('username', None)
    # Redirect to Login Page
    return redirect(url_for('Login'))

@app.route("/teacher/home")
def THome():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    if 'loggedin' in session and 'teacher' in session:
        t_id = session['teacher_id']
        cursor.execute("SELECT * FROM teacher WHERE teacher_id = %s", (t_id))
        session['data'] = cursor.fetchall()
        session['date'] = datetoday2
        data = session['data']
        print('data :',data[0])
        cursor.execute("SELECT s.*, COUNT(ref_std_id) as totalstd FROM subject as s LEFT JOIN enroll as e ON s.s_id = e.ref_s_id WHERE ref_teacher_id = %s GROUP BY s.s_id ORDER BY s.s_id DESC", (t_id))
        subject = cursor.fetchall()
        print(subject)
        return render_template("/teacher/index.html", today_date=session['date'], user=data[0], teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'], subject=subject)
    return redirect(url_for('Login'))

@app.route("/teacher/edit/<id>", methods=['GET','POST'])
def GetUser(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    if 'loggedin' in session and 'teacher' in session:
        cursor.execute("SELECT * FROM teacher WHERE teacher_id = %s", (id))
        session['data'] = cursor.fetchall()
        data = session['data']
        print('data :',data[0])
        return render_template("/teacher/edit.html", user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])
    return redirect(url_for('Login'))
    
@app.route("/teacher/update/<id>", methods=['POST'])
def Update(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    msg = ''
    data = session['data']

    if 'loggedin' in session and 'teacher' in session:
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
                return render_template("/teacher/edit.html", msg=msg, user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])
    return redirect(url_for('Login'))
     
@app.route("/teacher/addsubject", methods=['GET','POST'])
def AddSubject():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    msg = ''
    data = session['data']
    teacher_id = session['teacher_id']

    if 'loggedin' in session and 'teacher' in session:

        if request.method == 'POST' and 'subject_id' in request.form and 'subject' in request.form and 'start' in request.form and 'end' in request.form:
            subject_id = request.form['subject_id']
            subject = request.form['subject']
            start = request.form['start']
            end = request.form['end']
            print(subject_id, subject, start, end, teacher_id)

            cursor.execute("SELECT * from subject WHERE s_id = %s AND ref_teacher_id = %s", (subject_id, teacher_id))
            subject_check = cursor.fetchone()
            print(subject_check)

            if subject_check:
                msg = 'คุณเคยเพิ่มรายวิชานี้ไปแล้ว'
            elif not subject_check and subject_id != '' and subject != '' and start != '' and end != '':
                cursor.execute("INSERT INTO subject (s_id, s_name, start_time, end_time, ref_teacher_id) VALUES (%s,%s,%s,%s,%s)", (subject_id, subject, start, end, teacher_id))
                db.commit()
                msg = 'เพิ่มรายวิชาเรียบร้อย'
            else:
                msg = 'กรุณากรอกข้อมูล'
                return render_template("/teacher/addsubject.html", msg=msg, user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])
            return render_template("/teacher/addsubject.html", msg=msg, user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])
        return render_template("/teacher/addsubject.html", user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])
    return redirect(url_for('Login'))

@app.route('/teacher/checkin/<s_id>/<today_date>',methods=['GET','POST'])
def Checkin(s_id, today_date):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['data']
    teacher_id = session['teacher_id']
    cursor.execute("SELECT s.*, COUNT(ref_std_id) as totalstd FROM subject as s LEFT JOIN enroll as e ON s.s_id = e.ref_s_id WHERE ref_teacher_id = %s GROUP BY s.s_id ORDER BY s.s_id DESC", (teacher_id))
    subject = cursor.fetchall()
    print(subject)

    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('index.html',msg='ยังไม่มีข้อมูลใบหน้าใน model')
    
    print('checkindate :',today_date, type(today_date))
    cap = cv2.VideoCapture(0)
    ret = True
    while ret:
        ret, frame = cap.read()
        print(extract_faces(frame))
        if extract_faces(frame) != ():
            (x,y,w,h) = extract_faces(frame)[0]
            cv2.rectangle(frame,(x,y), (x+w, y+h), (255, 0, 20), 2)
            face = cv2.resize(frame[y:y+h,x:x+w], (50, 50))
            identified_person = identify_face(face.reshape(1,-1))[0]
            # add_attendance(identified_person, s_id, today_date)
            cv2.putText(frame,f'{identified_person}',(30,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255, 0, 20),2,cv2.LINE_AA)
            cv2.imshow('Attendance', frame)
            servo.cam_move(servo_pin)
        
        if cv2.waitKey(1)& 0xFF == ord('q'):
            add_attendance(identified_person, s_id, today_date)
            break

    cap.release()
    cv2.destroyAllWindows()
    print('stop')
    return render_template("/teacher/index.html", today_date=today_date, user=data[0], teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'], subject=subject)

@app.route("/teacher/checkinHistory/<s_id>", methods=['GET','POST'])
def CheckinHist(s_id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['data']
    teacher_id = session['teacher_id']

    if 'loggedin' in session and 'teacher' in session:
        print(s_id, teacher_id)
        cursor.execute("SELECT DATE(check_in_date) as a FROM checkin WHERE ref_s_id=%s AND ref_teacher_id=%s GROUP BY check_in_date", (s_id ,teacher_id))
        hist = cursor.fetchall()
        print(hist)
        cursor.execute("SELECT s_id,s_name FROM subject WHERE s_id=%s", (s_id))
        subject = cursor.fetchone()
        print(subject)
        return render_template("/teacher/checkin_history.html", hist=hist, s_id=s_id, user=data[0],teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'], subject=subject)
    return redirect(url_for('Login'))

@app.route("/teacher/checkDetailbyDate/<date>/<s_id>", methods=['GET','POST'])
def CheckDetailbyDate(date, s_id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['data']
    cursor.execute("SELECT start_time,end_time FROM subject WHERE s_id=%s",(s_id))
    late_check = cursor.fetchone()
    print(late_check)
    totalCome = 0
    totalLate = 0
    totalMiss = 0

    if 'loggedin' in session and 'teacher' in session:
        cursor.execute("SELECT s.*, i.check_in_status, TIME(i.date_save) AS check_in_time, i.no FROM student AS s \
                       JOIN checkin AS i ON s.std_id=i.ref_std_id\
                       WHERE i.ref_s_id=%s AND i.check_in_date=%s\
                       GROUP BY i.ref_std_id ORDER BY check_in_time ASC",
                       (s_id, date))
        checkin_data = cursor.fetchall()
        print(checkin_data)
        cursor.execute("SELECT s_id,s_name FROM subject WHERE s_id=%s", (s_id))
        subject = cursor.fetchone()
        print(subject)
        cursor.execute("SELECT s.*, COUNT(ref_std_id) as totalstd FROM subject as s LEFT JOIN enroll as e ON s.s_id = e.ref_s_id WHERE s.s_id=%s GROUP BY s.s_id ORDER BY s.s_id DESC",(s_id))
        subject2 = cursor.fetchone()
        print(subject2)

        for i in checkin_data:
            if i['check_in_status'] == 0:
                totalMiss+=1
            elif i['check_in_status'] == 1:
                totalCome+=1
            else:
                totalLate+=1

        #กรณีดึงข้อมูลไม่ได้ จะกลับไปยังหน้าหลัก
        if len(checkin_data) < 1:
            return redirect(url_for('THome'))
        return render_template("/teacher/checkin_hist_view.html",subject2=subject2,totalCome=totalCome,totalLate=totalLate,totalMiss=totalMiss, subject=subject, late_check=late_check, user=data[0], s_id=s_id, date=date, checkin_data=checkin_data,teacher_id=session['teacher_id'], teacher_name=session['teacher_name'], username=session['username'])



# ---------------- student section ---------------- #

@app.route("/student/logout")
def StdLogout():
    # Remove session data. This will log user out.
    session.pop('loggedin', None)
    session.pop('std', None)
    session.pop('std_id', None)
    session.pop('std_name', None)
    session.pop('username', None)
    # Redirect to Login Page
    return redirect(url_for('Login'))

@app.route("/student/home")
def StdHome():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    std_id = session['std_id']
    if 'loggedin' in session and 'std' in session:
        cursor.execute("SELECT s.*, COUNT(ref_std_id) as totalstd FROM subject as s LEFT JOIN enroll as e ON s.s_id = e.ref_s_id GROUP BY s.s_id ORDER BY s.s_id DESC")
        subject = cursor.fetchall()
        print(subject)
        cursor.execute("SELECT subject.s_name, ref_s_id FROM subject INNER JOIN enroll ON subject.s_id=ref_s_id WHERE enroll.ref_std_id=%s", (std_id))
        enroll = cursor.fetchall()
        cursor.execute("SELECT * FROM student WHERE std_id = %s", (std_id))
        session['std_data'] = cursor.fetchall()
        data = session['std_data']
        return render_template("/student/index.html", user=data[0], std_id=std_id, std_name=session['std_name'], username=session['username'], enroll=enroll, subject=subject)
    return redirect(url_for('Login'))    

@app.route("/student/edit/<id>", methods=['GET','POST'])
def GetStd(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    std_id = session['std_id']
    if 'loggedin' in session and 'std' in session:
        cursor.execute("SELECT * FROM student WHERE std_id = %s", (id))
        session['std_data'] = cursor.fetchall()
        data = session['std_data']
        print(data[0])
        return render_template("/student/edit.html", user=data[0],std_id=std_id, std_name=session['std_name'], username=session['username'])
    return redirect(url_for('Login'))
    
@app.route("/student/update/<id>", methods=['POST'])
def UpdateStd(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    msg = ''
    data = session['std_data']
    std_id = session['std_id']

    if 'loggedin' in session and 'std' in session:
        if request.method == 'POST' and 'username' in request.form and 'std_name' in request.form:
            name = request.form['std_name']
            username = request.form['username']
            cursor.execute("\
                        UPDATE student\
                        SET std_name = %s,\
                            username = %s\
                        WHERE std_id = %s\
                        ", (name, username, id))
            db.commit()

            old_imgfolder = 'static/faces/'+session['username']+'_'+str(std_id)
            cnt = 0    

            for filename in os.listdir(old_imgfolder):
                source = old_imgfolder + '/' + filename
                dest = old_imgfolder + '/' + username + '_' + str(cnt) + ".jpg"
                os.rename(source, dest)
                cnt += 1

            os.rename(old_imgfolder, "static/faces/"+username+'_'+str(id))
            

            return redirect(url_for('Login'))
        elif request.method == 'POST' and 'password' in request.form and 'conf_pw' in request.form:
            password = request.form['password']
            conf_pw = request.form['conf_pw']

            if password == conf_pw:
                cursor.execute("\
                            UPDATE student\
                            SET password = %s,\
                                conf_password = %s\
                            WHERE std_id = %s\
                            ", (password, conf_pw, id))
                db.commit()
                return redirect(url_for('Login'))
            else:
                msg = 'Password did not match'
                return render_template("/teacher/edit.html", msg=msg, user=data[0],std_id=std_id, std_name=session['std_name'], username=session['username'])
    return redirect(url_for('Login'))

@app.route("/student/enroll")
def EnrollPage():
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['std_data']
    std_id = session['std_id']

    if 'loggedin' in session and 'std' in session:
        cursor.execute("SELECT subject.*, teacher.teacher_name from subject inner join teacher on ref_teacher_id=teacher_id")
        subject = cursor.fetchall()
        print(subject)
        return render_template("/student/enroll.html", user=data[0], subject=subject,std_id=std_id, std_name=session['std_name'], username=session['username'])
    return redirect(url_for('Login'))

@app.route('/student/enroll/<id>', methods=['GET','POST'])
def Detail(id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['std_data']
    std_id = session['std_id']

    if 'loggedin' in session and 'std' in session:
        cursor.execute("SELECT subject.*, teacher.teacher_name from subject inner join teacher on ref_teacher_id=teacher_id WHERE s_id = %s", (id))
        subject = cursor.fetchone()
        print(subject)
        if request.method == 'POST' and 'subject_id' in request.form and 'subject' in request.form and 'start' in request.form and 'end' in request.form:
            subject_id = request.form['subject_id']
            std_id = session['std_id']
            print(subject_id, std_id)
            cursor.execute("SELECT * from enroll WHERE ref_s_id = %s AND ref_std_id = %s", (subject_id, std_id))
            enroll_check = cursor.fetchone()

            if enroll_check:
                msg = 'คุณเคยลงทะเบียนรายวิชานี้ไปแล้ว'
            else:
                cursor.execute("INSERT INTO enroll (ref_s_id, ref_std_id) VALUES (%s,%s)", (subject_id, std_id))
                db.commit()
                msg = 'ลงทะเบียนเรียบร้อย'
            return render_template("/student/detail.html", msg=msg, user=data[0], subject=subject,std_id=std_id, std_name=session['std_name'], username=session['username'])
        return render_template("/student/detail.html", user=data[0], subject=subject,std_id=std_id, std_name=session['std_name'], username=session['username'])
    return redirect(url_for('Login'))

@app.route("/student/checkinHistory/<s_id>", methods=['GET','POST'])
def StdCheckinHist(s_id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['data']
    std_id = session['std_id']

    if 'loggedin' in session and 'std' in session:
        print(s_id, std_id)
        cursor.execute("SELECT check_in_date FROM checkin WHERE ref_s_id=%s AND ref_std_id=%s GROUP BY check_in_date", (s_id ,std_id))
        hist = cursor.fetchall()
        print(hist)
        return render_template("/student/checkin_history.html", hist=hist, s_id=s_id, user=data[0],std_id=session['std_id'], std_name=session['std_name'], username=session['username'])
    return redirect(url_for('Login'))

@app.route("/student/checkDetailbyDate/<date>/<s_id>", methods=['GET','POST'])
def StdCheckDetailbyDate(date, s_id):
    db = mysql.connect()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    data = session['data']
    std_id = session['std_id']
    cursor.execute("SELECT start_time FROM subject WHERE s_id=%s",(s_id))
    late_check = cursor.fetchone()
    print(late_check)

    if 'loggedin' in session and 'std' in session:
        cursor.execute("SELECT s.*, i.check_in_status, TIME(i.date_save) AS check_in_time, i.no FROM student AS s \
                       JOIN checkin AS i ON s.std_id=i.ref_std_id\
                       WHERE i.ref_s_id=%s AND i.check_in_date=%s AND s.std_id = %s\
                       GROUP BY i.ref_std_id ORDER BY check_in_time ASC",
                       (s_id, date, std_id))
        checkin_data = cursor.fetchall()
        print(checkin_data)
        cursor.execute("SELECT s_id,s_name FROM subject WHERE s_id=%s", (s_id))
        subject = cursor.fetchone()
        print(subject)

        #กรณีดึงข้อมูลไม่ได้ จะกลับไปยังหน้าหลัก
        if len(checkin_data) < 1:
            return redirect(url_for('StdHome'))
        return render_template("/student/checkin_hist_view.html",subject=subject, late_check=late_check, user=data[0], s_id=s_id, date=date, checkin_data=checkin_data,std_id=session['std_id'], std_name=session['std_name'], username=session['username'])

# start app
if __name__ == "__main__":
    app.run(port=4000, debug=True)