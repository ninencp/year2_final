import mysql.connector
import datetime

mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    db='iot_project'
)

mycursor = mydb.cursor()

# mycursor.execute("CREATE DATABASE iot_project")

# mycursor.execute("CREATE TABLE student \
#                  (\
#                  std_id int NOT NULL PRIMARY KEY,\
#                  std_name varchar(50) NOT NULL,\
#                  username varchar(50) NOT NULL,\
#                  password varchar(50) NOT NULL,\
#                  conf_password varchar(50) NOT NULL\
#                  )")

# mycursor.execute("CREATE TABLE teacher (\
#                  teacher_id int NOT NULL PRIMARY KEY AUTO_INCREMENT,\
#                  teacher_name varchar(50) NOT NULL,\
#                  username varchar(50) NOT NULL,\
#                  password varchar(50) NOT NULL,\
#                  conf_password varchar(50) NOT NULL\
#                  )")

mycursor.execute("CREATE TABLE subject (\
                 s_id int NOT NULL PRIMARY KEY,\
                 s_name varchar(100),\
                 start_time varchar(10) NOT NULL,\
                 end_time varchar(10) NOT NULL,\
                 ref_teacher_id int NOT NULL COMMENT 'id อาจารย์',\
                 FOREIGN KEY (ref_teacher_id) REFERENCES teacher(teacher_id) \
                 )")

# mycursor.execute("CREATE TABLE enroll (\
#                  enroll_id int NOT NULL PRIMARY KEY AUTO_INCREMENT,\
#                  ref_s_id int NOT NULL COMMENT 'id วิชา',\
#                  FOREIGN KEY (ref_s_id) REFERENCES subject(s_id) ,\
#                  ref_std_id int NOT NULL COMMENT 'id นิสิต', \
#                  FOREIGN KEY (ref_std_id) REFERENCES student(std_id) \
#                  )")

# mycursor.execute("CREATE TABLE checkin (\
#                  no int PRIMARY KEY NOT NULL AUTO_INCREMENT,\
#                  ref_teacher_id int NOT NULL COMMENT 'id อาจารย์',\
#                  FOREIGN KEY (ref_teacher_id) REFERENCES teacher(teacher_id),\
#                  ref_s_id int NOT NULL COMMENT 'id วิชา',\
#                  FOREIGN KEY (ref_s_id) REFERENCES subject(s_id),\
#                  ref_std_id int NOT NULL COMMENT 'id นิสิต',\
#                  FOREIGN KEY (ref_std_id) REFERENCES student(std_id),\
#                  check_in_status int(1) NOT NULL COMMENT '0 ขาด 1 มา 2 สาย',\
#                  check_in_date timestamp NOT NULL,\
#                  date_save timestamp NOT NULL DEFAULT current_timestamp()\
#                  )")

# Insert data to session
# today = datetime.date.today()
# date_time = datetime.datetime.now()
# time_change = datetime.timedelta(hours=2,minutes=50)
# new = date_time + time_change

# start = date_time.strftime("%H:%M:%S")
# end = new.strftime("%H:%M:%S")
# print(today, start, end)

# sql = "INSERT INTO session (date, start_time, end_time, course_id) VALUES (%s, %s, %s, %s)"
# val = [(today,start,end,89022464)]
# mycursor.executemany(sql,val)

# mycursor.execute("INSERT INTO teacher (name, email, password, conf_password) VALUES ('สมชาย ใจดี', 'somchai@mail.com', 123456, 123456)")

# mycursor.execute("INSERT INTO course (course_id, name, teacher_id) VALUES(89022464, 'Internet of Things', 1)")

mydb.commit()