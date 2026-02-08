from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import flash
import db
import connect
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = 'sds_secret_2025'

# Initialize database connection
db.init_db(
    app, connect.dbuser, connect.dbpass, connect.dbhost, connect.dbname, connect.dbport
)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/teachers", methods=["GET"])
def teacher_list():
    cursor = db.get_cursor()
    querystr = "SELECT teacher_id, first_name, last_name, email, phone, is_active FROM teachers ORDER BY last_name, first_name;" 
    cursor.execute(querystr)        
    teachers = cursor.fetchall()
    cursor.close()
    return render_template("teacher_list.html", teachers=teachers)


@app.route("/students")
def student_list():
    cursor = db.get_cursor()
    search = request.args.get('search', '')
    
    if search:
        querystr = """
            SELECT student_id, first_name, last_name, email, phone, 
                   date_of_birth, enrollment_date, is_active 
            FROM students 
            WHERE first_name LIKE %s OR last_name LIKE %s
            ORDER BY last_name, first_name
        """
        cursor.execute(querystr, (f"%{search}%", f"%{search}%"))
    else:
        querystr = """
            SELECT student_id, first_name, last_name, email, phone, 
                   date_of_birth, enrollment_date, is_active 
            FROM students 
            ORDER BY last_name, first_name
        """
        cursor.execute(querystr)
    
    students = cursor.fetchall()
    cursor.close()
    
    return render_template("student_list.html", students=students, search=search)


@app.route("/students/<int:student_id>")
def student_summary(student_id):
    cursor = db.get_cursor()
    
    # Get student details
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        flash("Student not found", "error")
        return redirect(url_for('student_list'))
    
    # Get classes for this student
    querystr = """
        SELECT c.class_name, dt.dancetype_name, g.grade_name,
               t.first_name, t.last_name, c.schedule_day, c.schedule_time
        FROM classes c
        JOIN studentclasses sc ON c.class_id = sc.class_id
        JOIN dancetype dt ON c.dancetype_id = dt.dancetype_id
        LEFT JOIN grades g ON c.grade_id = g.grade_id
        JOIN teachers t ON c.teacher_id = t.teacher_id
        WHERE sc.student_id = %s
        ORDER BY dt.dancetype_name
    """
    cursor.execute(querystr, (student_id,))
    classes = cursor.fetchall()
    
    cursor.close()
    return render_template("student_summary.html", student=student, classes=classes)


@app.route("/classes")
def class_list():
    cursor = db.get_cursor()
    querystr = """
        SELECT c.class_id, c.class_name, dt.dancetype_name, g.grade_name,
               t.first_name, t.last_name, c.schedule_day, c.schedule_time
        FROM classes c
        JOIN dancetype dt ON c.dancetype_id = dt.dancetype_id
        LEFT JOIN grades g ON c.grade_id = g.grade_id
        JOIN teachers t ON c.teacher_id = t.teacher_id
        ORDER BY dt.dancetype_name, g.grade_level
    """
    cursor.execute(querystr)
    classes = cursor.fetchall()
    
    # Get students for each class
    for cls in classes:
        cursor.execute("""
            SELECT s.student_id, s.first_name, s.last_name
            FROM students s
            JOIN studentclasses sc ON s.student_id = sc.student_id
            WHERE sc.class_id = %s
            ORDER BY s.last_name, s.first_name
        """, (cls['class_id'],))
        cls['students'] = cursor.fetchall()
    
    cursor.close()
    return render_template("class_list.html", classes=classes)


@app.route("/enrol/<int:student_id>", methods=["GET", "POST"])
def enrol_student(student_id):
    cursor = db.get_cursor()
    
    if request.method == "POST":
        class_id = request.form['class_id']
        
        # Check if already enrolled
        cursor.execute(
            "SELECT * FROM studentclasses WHERE student_id = %s AND class_id = %s",
            (student_id, class_id)
        )
        if cursor.fetchone():
            flash("Student is already enrolled in this class", "error")
        else:
            cursor.execute(
                "INSERT INTO studentclasses (student_id, class_id) VALUES (%s, %s)",
                (student_id, class_id)
            )
            db.get_db().commit()
            flash("Student enrolled successfully", "success")
        
        cursor.close()
        return redirect(url_for('student_summary', student_id=student_id))
    
    # Get student name for display
    cursor.execute("SELECT student_id, first_name, last_name FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        flash("Student not found", "error")
        cursor.close()
        return redirect(url_for('student_list'))
    
    # Get student's current grades for each dance type
    cursor.execute("""
        SELECT sg.dancetype_id, dt.dancetype_name, MAX(g.grade_level) as current_grade_level
        FROM studentgrades sg
        JOIN grades g ON sg.grade_id = g.grade_id
        JOIN dancetype dt ON sg.dancetype_id = dt.dancetype_id
        WHERE sg.student_id = %s
        GROUP BY sg.dancetype_id
    """, (student_id,))
    student_grades = cursor.fetchall()
    
    # If student has no grades, they can only enrol in beginner classes (grade_level <= 1)
    qualified_classes = []
    
    if student_grades:
        # Student has some grades - check qualified classes for each dance type
        for grade in student_grades:
            cursor.execute("""
                SELECT c.class_id, c.class_name, dt.dancetype_name, g.grade_name, g.grade_level
                FROM classes c
                JOIN dancetype dt ON c.dancetype_id = dt.dancetype_id
                JOIN grades g ON c.grade_id = g.grade_id
                WHERE c.dancetype_id = %s 
                AND g.grade_level BETWEEN %s AND %s + 1
                AND c.class_id NOT IN (
                    SELECT class_id FROM studentclasses WHERE student_id = %s
                )
                ORDER BY g.grade_level, c.class_name
            """, (grade['dancetype_id'], grade['current_grade_level'], grade['current_grade_level'], student_id))
            qualified_classes.extend(cursor.fetchall())
    else:
        # Student has no grades - show beginner classes only (grade_level <= 1)
        cursor.execute("""
            SELECT c.class_id, c.class_name, dt.dancetype_name, g.grade_name, g.grade_level
            FROM classes c
            JOIN dancetype dt ON c.dancetype_id = dt.dancetype_id
            JOIN grades g ON c.grade_id = g.grade_id
            WHERE g.grade_level <= 1
            AND c.class_id NOT IN (
                SELECT class_id FROM studentclasses WHERE student_id = %s
            )
            ORDER BY dt.dancetype_name, g.grade_level
        """, (student_id,))
        qualified_classes = cursor.fetchall()
    
    cursor.close()
    return render_template("enrol_student.html", student=student, classes=qualified_classes)


@app.route("/students/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        date_of_birth = request.form.get('date_of_birth')
        enrollment_date = request.form.get('enrollment_date') or datetime.now().date().isoformat()
        
        # Basic validation
        errors = []
        if not first_name or not last_name:
            errors.append("First name and last name are required")
        
        if date_of_birth and date_of_birth > datetime.now().date().isoformat():
            errors.append("Date of birth cannot be in the future")
        
        if enrollment_date > datetime.now().date().isoformat():
            errors.append("Enrollment date cannot be in the future")
        
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add_student.html")
        
        # Insert student
        cursor = db.get_cursor()
        cursor.execute("""
            INSERT INTO students (first_name, last_name, email, phone, 
                                 date_of_birth, enrollment_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, email, phone, date_of_birth, enrollment_date))
        db.get_db().commit()
        
        student_id = cursor.lastrowid
        cursor.close()
        
        flash("Student added successfully", "success")
        return redirect(url_for('student_summary', student_id=student_id))
    
    return render_template("add_student.html")


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    cursor = db.get_cursor()
    
    if request.method == "POST":
        # ALWAYS update student info first (regardless of what button was clicked)
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        date_of_birth = request.form.get('date_of_birth')
        is_active = 'is_active' in request.form
        
        if not first_name or not last_name:
            flash("First name and last name are required", "error")
            return redirect(url_for('edit_student', student_id=student_id))
        
        # Update student information
        cursor.execute("""
            UPDATE students 
            SET first_name = %s, last_name = %s, email = %s, 
                phone = %s, date_of_birth = %s, is_active = %s
            WHERE student_id = %s
        """, (first_name, last_name, email, phone, date_of_birth, is_active, student_id))
        db.get_db().commit()
        
        # THEN check if we should also add a new grade
        new_grade_id = request.form.get('new_grade_id')
        new_dancetype_id = request.form.get('new_dancetype_id')
        
        if new_grade_id and new_dancetype_id:
            # Check if this grade already exists for this student and dance type
            cursor.execute("""
                SELECT * FROM studentgrades 
                WHERE student_id = %s AND grade_id = %s AND dancetype_id = %s
            """, (student_id, new_grade_id, new_dancetype_id))
            
            if cursor.fetchone():
                flash("This grade already exists for the selected dance type", "warning")
            else:
                cursor.execute("""
                    INSERT INTO studentgrades (student_id, grade_id, dancetype_id)
                    VALUES (%s, %s, %s)
                """, (student_id, new_grade_id, new_dancetype_id))
                db.get_db().commit()
                flash("Student information updated and new grade added", "success")
        else:
            flash("Student information updated successfully", "success")
        
        cursor.close()
        return redirect(url_for('edit_student', student_id=student_id))
    
    # GET request - show form with current data
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        flash("Student not found", "error")
        cursor.close()
        return redirect(url_for('student_list'))
    
    # Get student's current grades
    cursor.execute("""
        SELECT sg.studentgrade_id, g.grade_name, dt.dancetype_name
        FROM studentgrades sg
        JOIN grades g ON sg.grade_id = g.grade_id
        JOIN dancetype dt ON sg.dancetype_id = dt.dancetype_id
        WHERE sg.student_id = %s
        ORDER BY dt.dancetype_name
    """, (student_id,))
    grades = cursor.fetchall()
    
    # Get all available grades and dance types for the dropdowns
    cursor.execute("SELECT grade_id, grade_name FROM grades ORDER BY grade_level")
    all_grades = cursor.fetchall()
    
    cursor.execute("SELECT dancetype_id, dancetype_name FROM dancetype ORDER BY dancetype_name")
    all_dancetypes = cursor.fetchall()
    
    cursor.close()
    return render_template("edit_student.html", student=student, grades=grades, 
                          all_grades=all_grades, all_dancetypes=all_dancetypes)


@app.route("/students/grades/<int:studentgrade_id>/delete", methods=["POST"])
def delete_student_grade(studentgrade_id):
    cursor = db.get_cursor()
    
    # Get student_id for redirect
    cursor.execute("SELECT student_id FROM studentgrades WHERE studentgrade_id = %s", (studentgrade_id,))
    result = cursor.fetchone()
    
    if result:
        student_id = result['student_id']
        cursor.execute("DELETE FROM studentgrades WHERE studentgrade_id = %s", (studentgrade_id,))
        db.get_db().commit()
        flash("Grade deleted successfully", "success")
    else:
        flash("Grade not found", "error")
        student_id = None
    
    cursor.close()
    
    if student_id:
        return redirect(url_for('edit_student', student_id=student_id))
    else:
        return redirect(url_for('student_list'))


@app.route("/teachers/report")
def teacher_report():
    cursor = db.get_cursor()
    
    # Get teacher classes with student counts
    cursor.execute("""
        SELECT t.teacher_id, t.first_name, t.last_name,
               c.class_id, c.class_name, dt.dancetype_name,
               COUNT(sc.student_id) as student_count
        FROM teachers t
        JOIN classes c ON t.teacher_id = c.teacher_id
        JOIN dancetype dt ON c.dancetype_id = dt.dancetype_id
        LEFT JOIN studentclasses sc ON c.class_id = sc.class_id
        GROUP BY t.teacher_id, c.class_id
        ORDER BY t.last_name, t.first_name
    """)
    classes = cursor.fetchall()
    
    # Calculate unique students per teacher
    cursor.execute("""
        SELECT t.teacher_id, COUNT(DISTINCT sc.student_id) as unique_students
        FROM teachers t
        JOIN classes c ON t.teacher_id = c.teacher_id
        LEFT JOIN studentclasses sc ON c.class_id = sc.class_id
        GROUP BY t.teacher_id
    """)
    unique_counts = {row['teacher_id']: row['unique_students'] for row in cursor.fetchall()}
    
    cursor.close()
    return render_template("teacher_report.html", classes=classes, unique_counts=unique_counts)