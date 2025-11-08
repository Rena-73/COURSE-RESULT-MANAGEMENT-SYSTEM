from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'secretkey'

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    # Students table
    cur.execute('''CREATE TABLE IF NOT EXISTS Student(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        roll_no TEXT,
                        name TEXT,
                        department TEXT,
                        year INTEGER)''')
    # Courses table
    cur.execute('''CREATE TABLE IF NOT EXISTS Course(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT,
                        name TEXT,
                        credits INTEGER)''')
    # Results table
    cur.execute('''CREATE TABLE IF NOT EXISTS Result(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        course_id INTEGER,
                        marks INTEGER,
                        FOREIGN KEY(student_id) REFERENCES Student(id),
                        FOREIGN KEY(course_id) REFERENCES Course(id))''')
    # Users table
    cur.execute('''CREATE TABLE IF NOT EXISTS User(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        student_id INTEGER)''')
    # Insert default admin if not exists
    cur.execute("SELECT * FROM User WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO User(username,password,role) VALUES('admin','admin123','admin')")
    conn.commit()
    conn.close()

init_db()

# --- Routes ---
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('crms.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM User WHERE username=? AND password=?", (username,password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['username'] = username
            session['role'] = user[3]
            session['student_id'] = user[4]  # None for admin
            if user[3] == 'admin':
                return redirect('/dashboard')
            else:
                return redirect('/student_dashboard')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

# --- Admin Dashboard ---
@app.route('/dashboard')
def dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Student")
    total_students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Course")
    total_courses = cur.fetchone()[0]
    # Average CGPA calculation
    cur.execute('''SELECT s.id, SUM(r.marks*c.credits)/SUM(c.credits) as cgpa
                   FROM Result r
                   JOIN Student s ON r.student_id = s.id
                   JOIN Course c ON r.course_id = c.id
                   GROUP BY s.id''')
    avg_cgpa = cur.fetchone()[1] if cur.fetchone() else 0
    conn.close()
    return render_template('dashboard.html', total_students=total_students,
                           total_courses=total_courses, avg_cgpa=avg_cgpa)

# --- Student Dashboard ---
@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect('/login')
    student_id = session.get('student_id')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Student WHERE id=?", (student_id,))
    student = cur.fetchone()
    conn.close()
    return render_template('student_dashboard.html', student_name=student[2], student_id=student_id)

# --- Student CRUD ---
@app.route('/add_student', methods=['GET','POST'])
def add_student():
    if session.get('role') != 'admin':
        return redirect('/login')
    if request.method=='POST':
        roll_no = request.form['roll_no']
        name = request.form['name']
        dept = request.form['department']
        year = request.form['year']
        conn = sqlite3.connect('crms.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO Student(roll_no,name,department,year) VALUES(?,?,?,?)",
                    (roll_no,name,dept,year))
        conn.commit()
        # Add user for student login
        cur.execute("SELECT id FROM Student WHERE roll_no=?", (roll_no,))
        student_id = cur.fetchone()[0]
        cur.execute("INSERT INTO User(username,password,role,student_id) VALUES(?,?,?,?)",
                    (name,'student123','student',student_id))
        conn.commit()
        conn.close()
        return redirect('/view_students')
    return render_template('add_student.html')

@app.route('/view_students')
def view_students():
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Student")
    data = cur.fetchall()
    conn.close()
    return render_template('view_students.html', students=data)

@app.route('/edit_student/<int:id>', methods=['GET','POST'])
def edit_student(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    if request.method=='POST':
        roll_no = request.form['roll_no']
        name = request.form['name']
        dept = request.form['department']
        year = request.form['year']
        cur.execute("UPDATE Student SET roll_no=?, name=?, department=?, year=? WHERE id=?",
                    (roll_no,name,dept,year,id))
        conn.commit()
        conn.close()
        return redirect('/view_students')
    cur.execute("SELECT * FROM Student WHERE id=?", (id,))
    student = cur.fetchone()
    conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:id>')
def delete_student(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM Student WHERE id=?", (id,))
    cur.execute("DELETE FROM User WHERE student_id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/view_students')

# --- Course CRUD ---
@app.route('/add_course', methods=['GET','POST'])
def add_course():
    if session.get('role') != 'admin':
        return redirect('/login')
    if request.method=='POST':
        code = request.form['code']
        name = request.form['name']
        credits = request.form['credits']
        conn = sqlite3.connect('crms.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO Course(code,name,credits) VALUES(?,?,?)", (code,name,credits))
        conn.commit()
        conn.close()
        return redirect('/view_courses')
    return render_template('add_course.html')

@app.route('/view_courses')
def view_courses():
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM Course")
    data = cur.fetchall()
    conn.close()
    return render_template('view_courses.html', courses=data)

@app.route('/edit_course/<int:id>', methods=['GET','POST'])
def edit_course(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    if request.method=='POST':
        code = request.form['code']
        name = request.form['name']
        credits = request.form['credits']
        cur.execute("UPDATE Course SET code=?, name=?, credits=? WHERE id=?",
                    (code,name,credits,id))
        conn.commit()
        conn.close()
        return redirect('/view_courses')
    cur.execute("SELECT * FROM Course WHERE id=?", (id,))
    course = cur.fetchone()
    conn.close()
    return render_template('edit_course.html', course=course)

@app.route('/delete_course/<int:id>')
def delete_course(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM Course WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/view_courses')

# --- Result CRUD ---
@app.route('/add_result', methods=['GET','POST'])
def add_result():
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM Student")
    students = cur.fetchall()
    cur.execute("SELECT id,name FROM Course")
    courses = cur.fetchall()
    if request.method=='POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        marks = request.form['marks']
        cur.execute("INSERT INTO Result(student_id,course_id,marks) VALUES(?,?,?)",
                    (student_id,course_id,marks))
        conn.commit()
        conn.close()
        return redirect('/view_results')
    conn.close()
    return render_template('add_result.html', students=students, courses=courses)

@app.route('/view_results')
def view_results():
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute('''SELECT r.id, s.name, c.name, r.marks
                   FROM Result r
                   JOIN Student s ON r.student_id=s.id
                   JOIN Course c ON r.course_id=c.id''')
    data = cur.fetchall()
    conn.close()
    return render_template('view_results.html', results=data)

@app.route('/edit_result/<int:id>', methods=['GET','POST'])
def edit_result(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("SELECT id,name FROM Student")
    students = cur.fetchall()
    cur.execute("SELECT id,name FROM Course")
    courses = cur.fetchall()
    if request.method=='POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        marks = request.form['marks']
        cur.execute("UPDATE Result SET student_id=?, course_id=?, marks=? WHERE id=?",
                    (student_id, course_id, marks, id))
        conn.commit()
        conn.close()
        return redirect('/view_results')
    cur.execute("SELECT * FROM Result WHERE id=?", (id,))
    result = cur.fetchone()
    conn.close()
    return render_template('edit_result.html', result=result, students=students, courses=courses)

@app.route('/delete_result/<int:id>')
def delete_result(id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM Result WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/view_results')

# --- Student Grade Card ---
@app.route('/grade_card/<int:student_id>')
def grade_card(student_id):
    conn = sqlite3.connect('crms.db')
    cur = conn.cursor()

    # Fetch student details
    cur.execute("SELECT * FROM Student WHERE id=?", (student_id,))
    student = cur.fetchone()  # [id, roll_no, name, department, year]

    # Fetch results for the student
    cur.execute('''SELECT c.name, r.marks 
                   FROM Result r 
                   JOIN Course c ON r.course_id = c.id 
                   WHERE r.student_id=?''', (student_id,))
    results = cur.fetchall()  # list of tuples [(course_name, marks), ...]

    # Calculate grades
    grades = []
    total_points = 0
    total_courses = len(results)
    for course_name, marks in results:
        if marks >= 90:
            grade = 'A+'
            point = 10
        elif marks >= 80:
            grade = 'A'
            point = 9
        elif marks >= 70:
            grade = 'B+'
            point = 8
        elif marks >= 60:
            grade = 'B'
            point = 7
        elif marks >= 50:
            grade = 'C'
            point = 6
        else:
            grade = 'F'
            point = 0
        grades.append(grade)
        total_points += point

    # Calculate CGPA
    cgpa = round(total_points / total_courses, 2) if total_courses > 0 else 0

    # Pre-zip results and grades
    combined = list(zip(results, grades))

    conn.close()
    return render_template('grade_card.html', student=student, combined=combined, cgpa=cgpa)


# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__=='__main__':
    app.run(debug=True)
