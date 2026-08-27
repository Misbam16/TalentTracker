import os
import pickle
import mysql.connector

from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename


app = Flask(__name__, template_folder="Templets")

app.secret_key = "talenttrack_secret_key"

# Upload folder
UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template('UserLogin.html')


# Load AI Career Prediction Model
model_path = os.path.join(
    os.path.dirname(__file__),
    "ML",
    "career_model.pkl"
)

with open(model_path, "rb") as file:
    model, label_encoder = pickle.load(file)


# MySQL connection
conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="root",
    database="talenttrack_ai",
    charset="utf8",
    collation="utf8_general_ci"
)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        query = """
        SELECT * FROM students
        WHERE email = %s AND password = %s
        """
        cursor = conn.cursor()
        values = (email, password)

        cursor.execute(query, values)
        student = cursor.fetchone()

        if student:

            # Student ID session me save
            session['student_id'] = student[0]

            return redirect('/dashboard')

        else:
            return "Invalid Email or Password!"

    return render_template('UserLogin.html')


@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    # =========================
    # SAVE PROFILE
    # =========================
    if request.method == "POST":

        # Create cursor BEFORE using cursor.execute()
        cursor = conn.cursor()

        dob = request.form.get('dob') or None
        gender = request.form.get('gender')
        address = request.form.get('address')
        semester = request.form.get('semester')
        tenth_percentage = request.form.get('tenth_percentage')
        twelfth_percentage = request.form.get('twelfth_percentage')
        graduation_percentage = request.form.get('graduation_percentage')
        python_skill = request.form.get('python_skill')
        java_skill = request.form.get('java_skill')
        sql_skill = request.form.get('sql_skill')

        # =========================
        # RESUME UPLOAD
        # =========================

        resume = request.files.get('resume')

        resume_path = None

        if resume and resume.filename != '':

            filename = secure_filename(resume.filename)

            filename = f"{student_id}_{filename}"

            filepath = os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )

            resume.save(filepath)

            resume_path = filepath.replace("\\", "/")

        # =========================
        # CHECK EXISTING PROFILE
        # =========================

        cursor=conn.cursor()
        cursor.execute(
            "SELECT profile_id, resume_path FROM student_profile WHERE student_id = %s",
            (student_id,)
        )

        existing_profile = cursor.fetchone()

        if existing_profile:

            # Keep old resume if no new resume uploaded
            if resume_path is None:
                resume_path = existing_profile[1]

            # =========================
            # UPDATE PROFILE
            # =========================

            query = """
            UPDATE student_profile
            SET
                dob = %s,
                gender = %s,
                address = %s,
                semester = %s,
                tenth_percentage = %s,
                twelfth_percentage = %s,
                graduation_percentage = %s,
                python_skill = %s,
                java_skill = %s,
                sql_skill = %s,
                resume_path = %s
            WHERE student_id = %s
            """

            values = (
                dob,
                gender,
                address,
                semester,
                tenth_percentage,
                twelfth_percentage,
                graduation_percentage,
                python_skill,
                java_skill,
                sql_skill,
                resume_path,
                student_id
            )

        else:

            # =========================
            # INSERT PROFILE
            # =========================

            query = """
            INSERT INTO student_profile
            (
                student_id,
                dob,
                gender,
                address,
                semester,
                tenth_percentage,
                twelfth_percentage,
                graduation_percentage,
                python_skill,
                java_skill,
                sql_skill,
                resume_path
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                student_id,
                dob,
                gender,
                address,
                semester,
                tenth_percentage,
                twelfth_percentage,
                graduation_percentage,
                python_skill,
                java_skill,
                sql_skill,
                resume_path
            )

        cursor.execute(query, values)

        conn.commit()

        cursor.close()

        return redirect('/profile')

    # =========================
    # DISPLAY PROFILE
    # =========================

    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        s.full_name,
        s.email,
        s.mobile,
        p.dob,
        p.gender,
        p.address,
        p.semester,
        p.tenth_percentage,
        p.twelfth_percentage,
        p.graduation_percentage,
        p.python_skill,
        p.java_skill,
        p.sql_skill,
        p.resume_path
    FROM students s
    LEFT JOIN student_profile p
        ON s.student_id = p.student_id
    WHERE s.student_id = %s
    """

    cursor.execute(query, (student_id,))

    student = cursor.fetchone()

    cursor.close()

    return render_template(
        "Student_profile.html",
        student=student
    )
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['full_name']
        email = request.form['email']
        mobile = request.form['mobile']
        course = request.form['course']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Password and Confirm Password do not match!"

        query = """
        INSERT INTO students
        (full_name, email, mobile, course, password)
        VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            name,
            email,
            mobile,
            course,
            password
        )

        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        cursor.close()

        return redirect('/login')

    return render_template('Register.html')

@app.route('/dashboard')
def dashboard():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # =========================
    # STUDENT PROFILE
    # =========================

    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # =========================
    # LATEST ASSESSMENT
    # =========================

    cursor.execute("""
        SELECT score, total_questions, percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    # =========================
    # DEFAULT VALUES
    # =========================

    prediction = None
    profile_completed = False
    assessment_completed = False

    # =========================
    # CHECK PROFILE
    # =========================

    if profile:
        profile_completed = True

    # =========================
    # CHECK ASSESSMENT
    # =========================

    if assessment:
        assessment_completed = True

    # =========================
    # AI PREDICTION
    # Only when both exist
    # =========================

    if profile and assessment:

        input_data = [[
            float(profile['python_skill'] or 0),
            float(profile['java_skill'] or 0),
            float(profile['sql_skill'] or 0),
            float(profile['tenth_percentage'] or 0),
            float(profile['twelfth_percentage'] or 0),
            float(profile['graduation_percentage'] or 0),
            float(assessment['percentage'] or 0)
        ]]

        prediction_number = model.predict(input_data)

        prediction = label_encoder.inverse_transform(
            prediction_number
        )[0]

    # =========================
    # OPEN DASHBOARD
    # =========================

    return render_template(
        'Dashboard.html',
        profile=profile,
        profile_completed=profile_completed,
        assessment=assessment,
        assessment_completed=assessment_completed,
        prediction=prediction
    )

@app.route('/ai-prediction')
def ai_prediction():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # Student Profile
    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # Latest Assessment Result
    cursor.execute("""
        SELECT score, total_questions, percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    # Profile nahi mila
    if not profile:
        return "Please complete your Student Profile first."

    # Assessment nahi diya
    if not assessment:
        return "Please complete the Skill Assessment first."

    # ML input - TOTAL 7 FEATURES
    input_data = [[
        float(profile['python_skill'] or 0),
        float(profile['java_skill'] or 0),
        float(profile['sql_skill'] or 0),
        float(profile['tenth_percentage'] or 0),
        float(profile['twelfth_percentage'] or 0),
        float(profile['graduation_percentage'] or 0),
        float(assessment['percentage'] or 0)
    ]]

    # Prediction
    prediction_number = model.predict(input_data)

    prediction = label_encoder.inverse_transform(
        prediction_number
    )[0]

    # Career information
    career_info = {

        "Python Developer": {
            "description": "Suitable for students interested in Python programming and application development.",
            "skills": "Python, Django/Flask, SQL, Git",
            "next_step": "Improve Python programming and build real-world projects."
        },

        "Java Developer": {
            "description": "Suitable for students interested in Java-based software and web application development.",
            "skills": "Java, OOP, JDBC, Spring Boot, SQL",
            "next_step": "Improve Java and Spring Boot skills and create projects."
        },

        "Data Analyst": {
            "description": "Suitable for students interested in data analysis and business insights.",
            "skills": "Python, SQL, Pandas, Excel",
            "next_step": "Learn data visualization and work on data analysis projects."
        },

        "Data Scientist": {
            "description": "Suitable for students interested in AI, machine learning and data science.",
            "skills": "Python, SQL, Pandas, Machine Learning",
            "next_step": "Learn ML algorithms and build machine learning projects."
        },

        "Web Developer": {
            "description": "Suitable for students interested in creating websites and web applications.",
            "skills": "HTML, CSS, JavaScript, Python/Java, SQL",
            "next_step": "Build responsive websites and full-stack projects."
        }
    }

    info = career_info.get(
        prediction,
        {
            "description": "Career recommendation based on your profile.",
            "skills": "Programming, Database and Problem Solving",
            "next_step": "Improve your technical skills and build projects."
        }
    )

    return render_template(
        'AI_prediction.html',
        prediction=prediction,
        profile=profile,
        assessment=assessment,
        info=info
    )

@app.route('/skill-gap')
def skill_gap():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # Student profile
    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # Latest assessment
    cursor.execute("""
        SELECT percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    if not profile:
        return "Please complete your Student Profile first."

    if not assessment:
        return "Please complete the Skill Assessment first."

    # Student skills
    python_skill = float(profile['python_skill'] or 0)
    java_skill = float(profile['java_skill'] or 0)
    sql_skill = float(profile['sql_skill'] or 0)

    assessment_percentage = float(
        assessment['percentage'] or 0
    )

    # Overall Skill Score
    overall_score = (
        python_skill +
        java_skill +
        sql_skill +
        assessment_percentage
    ) / 4

    # Career prediction
    input_data = [[
        python_skill,
        java_skill,
        sql_skill,
        float(profile['tenth_percentage'] or 0),
        float(profile['twelfth_percentage'] or 0),
        float(profile['graduation_percentage'] or 0),
        assessment_percentage
    ]]

    prediction_number = model.predict(input_data)

    prediction = label_encoder.inverse_transform(
        prediction_number
    )[0]

    # Skill requirements for each career
    career_skills = {

        "Python Developer": {
            "Python": python_skill,
            "Django/Flask": 0,
            "SQL": sql_skill,
            "Git": 0
        },

        "Java Developer": {
            "Java": java_skill,
            "OOP": 0,
            "JDBC": 0,
            "Spring Boot": 0,
            "SQL": sql_skill
        },

        "Data Analyst": {
            "Python": python_skill,
            "SQL": sql_skill,
            "Pandas": 0,
            "Excel": 0,
            "Data Visualization": 0
        },

        "Data Scientist": {
            "Python": python_skill,
            "SQL": sql_skill,
            "Pandas": 0,
            "Machine Learning": 0
        },

        "Web Developer": {
            "HTML": 0,
            "CSS": 0,
            "JavaScript": 0,
            "Python/Java": max(python_skill, java_skill),
            "SQL": sql_skill
        }
    }

    required_skills = career_skills.get(
        prediction,
        {}
    )

    # Skill gap calculation
    current_skills = []
    missing_skills = []

    for skill, level in required_skills.items():

        if level >= 50:
            current_skills.append(skill)
        else:
            missing_skills.append(skill)

    skill_gap_count = len(missing_skills)

    # Recommended learning path
    learning_path = []

    for skill in missing_skills:

        if skill == "Pandas":
            learning_path.append("Learn Pandas for Data Analysis")

        elif skill == "Excel":
            learning_path.append("Improve Excel and spreadsheet skills")

        elif skill == "Data Visualization":
            learning_path.append("Learn Matplotlib, Seaborn and Power BI")

        elif skill == "Machine Learning":
            learning_path.append("Learn Machine Learning concepts and algorithms")

        elif skill == "Django/Flask":
            learning_path.append("Learn Django or Flask")

        elif skill == "Git":
            learning_path.append("Learn Git and GitHub")

        elif skill == "Spring Boot":
            learning_path.append("Learn Spring Boot")

        elif skill == "JDBC":
            learning_path.append("Practice JDBC and database connectivity")

        elif skill == "OOP":
            learning_path.append("Strengthen Object-Oriented Programming concepts")

        elif skill == "JavaScript":
            learning_path.append("Improve JavaScript skills")

        elif skill == "CSS":
            learning_path.append("Improve CSS and responsive design")

        elif skill == "HTML":
            learning_path.append("Strengthen HTML fundamentals")

        else:
            learning_path.append("Improve " + skill + " skills")

    return render_template(
        'Skill_gap.html',
        prediction=prediction,
        current_skills=current_skills,
        missing_skills=missing_skills,
        skill_gap_count=skill_gap_count,
        learning_path=learning_path,
        python_skill=python_skill,
        java_skill=java_skill,
        sql_skill=sql_skill,
        assessment_percentage=assessment_percentage,
        overall_score=overall_score
    )
@app.route('/skill-progress')
def skill_progress():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # Student profile
    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # Latest assessment
    cursor.execute("""
        SELECT percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    # Profile check
    if not profile:
        return "Please complete your Student Profile first."

    # Assessment check
    if not assessment:
        return "Please complete the Skill Assessment first."

    # Student skills
    python_skill = float(profile['python_skill'] or 0)
    java_skill = float(profile['java_skill'] or 0)
    sql_skill = float(profile['sql_skill'] or 0)

    # Assessment percentage
    assessment_percentage = float(
        assessment['percentage'] or 0
    )

    # Technical skill score
    technical_score = (
        python_skill +
        java_skill +
        sql_skill
    ) / 3

    # Overall skill score
    overall_score = (
        technical_score * 0.6 +
        assessment_percentage * 0.4
    )

    return render_template(
        'Skill_progress.html',
        python_skill=python_skill,
        java_skill=java_skill,
        sql_skill=sql_skill,
        assessment_percentage=assessment_percentage,
        technical_score=technical_score,
        overall_score=overall_score
    )

@app.route('/learning-recommendations')
def learning_recommendations():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # Student profile
    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # Latest assessment
    cursor.execute("""
        SELECT percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    if not profile:
        return "Please complete your Student Profile first."

    if not assessment:
        return "Please complete the Skill Assessment first."

    # Student skills
    python_skill = float(profile['python_skill'] or 0)
    java_skill = float(profile['java_skill'] or 0)
    sql_skill = float(profile['sql_skill'] or 0)

    assessment_percentage = float(
        assessment['percentage'] or 0
    )

    # Career prediction
    input_data = [[
        python_skill,
        java_skill,
        sql_skill,
        float(profile['tenth_percentage'] or 0),
        float(profile['twelfth_percentage'] or 0),
        float(profile['graduation_percentage'] or 0),
        assessment_percentage
    ]]

    prediction_number = model.predict(input_data)

    prediction = label_encoder.inverse_transform(
        prediction_number
    )[0]

    # Learning recommendations
    recommendations = {

        "Python Developer": [
            "Learn Python advanced concepts",
            "Practice Django or Flask",
            "Improve SQL skills",
            "Learn Git and GitHub"
        ],

        "Java Developer": [
            "Strengthen Java OOP concepts",
            "Learn JDBC",
            "Learn Spring Boot",
            "Practice SQL",
            "Learn Git and GitHub"
        ],

        "Data Analyst": [
            "Learn Python for Data Analysis",
            "Practice SQL",
            "Learn Pandas",
            "Learn Excel",
            "Learn Data Visualization"
        ],

        "Data Scientist": [
            "Improve Python skills",
            "Learn Pandas and NumPy",
            "Learn Machine Learning",
            "Practice SQL",
            "Work on ML projects"
        ],

        "Web Developer": [
            "Learn HTML",
            "Learn CSS",
            "Improve JavaScript",
            "Learn Python or Java",
            "Practice SQL"
        ]
    }

    learning_path = recommendations.get(
        prediction,
        []
    )

    return render_template(
        'Learning_recommendations.html',
        prediction=prediction,
        learning_path=learning_path
    )

@app.route('/career-reports')
def career_reports():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    cursor = conn.cursor(dictionary=True)

    # Student profile
    cursor.execute("""
        SELECT *
        FROM student_profile
        WHERE student_id = %s
    """, (student_id,))

    profile = cursor.fetchone()

    # Latest assessment
    cursor.execute("""
        SELECT percentage
        FROM assessment_results
        WHERE student_id = %s
        ORDER BY result_id DESC
        LIMIT 1
    """, (student_id,))

    assessment = cursor.fetchone()

    cursor.close()

    # Profile check
    if not profile:
        return "Please complete your Student Profile first."

    # Assessment check
    if not assessment:
        return "Please complete the Skill Assessment first."

    # Student skills
    python_skill = float(profile['python_skill'] or 0)
    java_skill = float(profile['java_skill'] or 0)
    sql_skill = float(profile['sql_skill'] or 0)

    assessment_percentage = float(
        assessment['percentage'] or 0
    )

    # Career prediction
    input_data = [[
        python_skill,
        java_skill,
        sql_skill,
        float(profile['tenth_percentage'] or 0),
        float(profile['twelfth_percentage'] or 0),
        float(profile['graduation_percentage'] or 0),
        assessment_percentage
    ]]

    prediction_number = model.predict(input_data)

    prediction = label_encoder.inverse_transform(
        prediction_number
    )[0]

    # Current and missing skills
    current_skills = []
    missing_skills = []

    skill_values = {
        "Python": python_skill,
        "Java": java_skill,
        "SQL": sql_skill
    }

    for skill, level in skill_values.items():

        if level >= 50:
            current_skills.append(skill)
        else:
            missing_skills.append(skill)

    # Learning recommendations
    recommendations = {

        "Python Developer": [
            "Learn advanced Python",
            "Practice Django or Flask",
            "Improve SQL",
            "Learn Git and GitHub"
        ],

        "Java Developer": [
            "Strengthen Java and OOP",
            "Learn JDBC",
            "Learn Spring Boot",
            "Practice SQL",
            "Learn Git and GitHub"
        ],

        "Data Analyst": [
            "Learn Python for Data Analysis",
            "Practice SQL",
            "Learn Pandas",
            "Learn Excel",
            "Learn Data Visualization"
        ],

        "Data Scientist": [
            "Improve Python",
            "Learn Pandas and NumPy",
            "Learn Machine Learning",
            "Practice SQL",
            "Build ML projects"
        ],

        "Web Developer": [
            "Learn HTML and CSS",
            "Improve JavaScript",
            "Learn Python or Java",
            "Practice SQL",
            "Build full-stack projects"
        ]
    }

    learning_path = recommendations.get(
        prediction,
        []
    )

    # Overall score
    technical_score = (
        python_skill +
        java_skill +
        sql_skill
    ) / 3

    overall_score = (
        technical_score * 0.6 +
        assessment_percentage * 0.4
    )

    return render_template(
        'Career_reports.html',
        prediction=prediction,
        python_skill=python_skill,
        java_skill=java_skill,
        sql_skill=sql_skill,
        assessment_percentage=assessment_percentage,
        current_skills=current_skills,
        missing_skills=missing_skills,
        learning_path=learning_path,
        overall_score=overall_score
    )

@app.route('/skill-assessment')
def Skill_assessment():
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM assessment_questions
        ORDER BY question_id
    """

    cursor.execute(query)

    questions = cursor.fetchall()

    cursor.close()

    return render_template(
        'Skill_assessment.html',
        questions=questions
    )

@app.route('/submit-assessment', methods=['POST'])
def submit_assessment():

    if 'student_id' not in session:
        return redirect('/login')

    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM assessment_questions
        ORDER BY question_id
    """

    cursor.execute(query)
    questions = cursor.fetchall()

    score = 0

    for question in questions:

        question_id = str(question['question_id'])

        selected_answer = request.form.get(
            'question_' + question_id
        )

        if selected_answer == question['correct_answer']:
            score += 1

    total_questions = len(questions)

    percentage = (score / total_questions) * 100

    # Existing assessment_results table mein result save
    insert_query = """
        INSERT INTO assessment_results
        (student_id, score, total_questions, percentage)
        VALUES (%s, %s, %s, %s)
    """

    values = (
        session['student_id'],
        score,
        total_questions,
        percentage
    )

    cursor.execute(insert_query, values)

    conn.commit()

    cursor.close()
    
    return render_template(
    'Assessment_result.html',
    score=score,
    total_questions=total_questions,
    percentage=percentage
)

@app.route('/settings')
def settings():

    if 'student_id' not in session:
        return redirect('/login')

    return render_template('Settings.html')

@app.route('/logout')
def logout():
    if 'student_id' not in session:
        return redirect('/login')

    return render_template('logout.html')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():

    if 'student_id' not in session:
        return redirect('/login')

    student_id = session['student_id']

    if request.method == 'POST':

        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check current password
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT password
            FROM students
            WHERE student_id = %s
        """, (student_id,))

        student = cursor.fetchone()

        if not student:
            cursor.close()
            return "Student not found."

        # Check old password
        if student['password'] != current_password:
            cursor.close()
            return "Current password is incorrect."

        # Check new password
        if new_password != confirm_password:
            cursor.close()
            return "New password and confirm password do not match."

        # Update password
        cursor.execute("""
            UPDATE students
            SET password = %s
            WHERE student_id = %s
        """, (new_password, student_id))

        conn.commit()
        cursor.close()

        return redirect('/settings')

    return render_template('Change_password.html')

@app.route('/logout')
def logout_page():

    if 'student_id' not in session:
        return redirect('/login')

    return render_template('Logout.html')

@app.route('/logout-confirm')
def logout_confirm():

    session.clear()

    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
