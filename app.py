from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db_connection
import re

app = Flask(__name__)
app.secret_key = "resumebuilder123"


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("home.html")


# =========================================================
# USER REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("user_email")
        password = request.form.get("user_password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                return render_template(
                    "register.html",
                    error="Email already registered."
                )

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (name, email, password)
            )

            connection.commit()

            return redirect(url_for("login"))

        except Exception as e:

            if connection:
                connection.rollback()

            return f"""
            <h2>Registration Error</h2>
            <p>{e}</p>
            <a href="/register">Go Back</a>
            """

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template("register.html")


# =========================================================
# USER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("user_email")
        password = request.form.get("user_password")

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT user_id, name, email
                FROM users
                WHERE email = %s
                AND password = %s
                """,
                (email, password)
            )

            user = cursor.fetchone()

            if user:

                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]

                return redirect(url_for("user_dashboard"))

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        except Exception as e:

            return f"""
            <h2>Login Error</h2>
            <p>{e}</p>
            <a href="/login">Go Back</a>
            """

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template("login.html")


# =========================================================
# USER DASHBOARD
# =========================================================

@app.route("/dashboard")
def user_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name")
    )


# =========================================================
# RESUME BUILDER
# =========================================================

@app.route("/resume-builder", methods=["GET", "POST"])
def resume_builder():

    if "user_id" not in session:
        return redirect(url_for("login"))

    template_id = request.args.get("template_id")

    if template_id:

        try:
            template_id = int(template_id)

        except (TypeError, ValueError):
            template_id = None

    # =====================================================
    # SAVE RESUME
    # =====================================================

    if request.method == "POST":

        template_id = request.form.get("template_id")

        if template_id:

            try:
                template_id = int(template_id)

            except (TypeError, ValueError):
                template_id = None

        # -------------------------------------------------
        # PERSONAL INFORMATION
        # -------------------------------------------------

        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")

        city = request.form.get("city")
        state = request.form.get("state")
        country = request.form.get("country")

        linkedin = request.form.get("linkedin")
        github = request.form.get("github")

        career_objective = request.form.get("career_objective")

        # -------------------------------------------------
        # DEFAULT ATS TEMPLATE
        # -------------------------------------------------

        if not template_id:

            template_connection = None
            template_cursor = None

            try:

                template_connection = get_db_connection()

                template_cursor = template_connection.cursor(
                    dictionary=True
                )

                template_cursor.execute(
                    """
                    SELECT template_id
                    FROM resume_templates
                    WHERE template_type = 'ATS'
                    ORDER BY template_id ASC
                    LIMIT 1
                    """
                )

                default_template = template_cursor.fetchone()

                if default_template:
                    template_id = default_template["template_id"]

            except Exception:

                template_id = None

            finally:

                if template_cursor:
                    template_cursor.close()

                if template_connection:
                    template_connection.close()

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            # =================================================
            # INSERT RESUME
            # =================================================

            cursor.execute(
                """
                INSERT INTO resumes
                (
                    user_id,
                    template_id,
                    full_name,
                    email,
                    phone,
                    city,
                    state,
                    country,
                    linkedin,
                    github,
                    career_objective
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    template_id,
                    full_name,
                    email,
                    phone,
                    city,
                    state,
                    country,
                    linkedin,
                    github,
                    career_objective
                )
            )

            resume_id = cursor.lastrowid

            # =================================================
            # EDUCATION
            # =================================================

            degrees = request.form.getlist("degree[]")
            institutions = request.form.getlist("institution[]")
            years = request.form.getlist("year[]")
            grades = request.form.getlist("grade[]")

            for i in range(len(degrees)):

                degree = degrees[i].strip() if i < len(degrees) else ""

                institution = (
                    institutions[i].strip()
                    if i < len(institutions)
                    else ""
                )

                year = years[i].strip() if i < len(years) else ""
                grade = grades[i].strip() if i < len(grades) else ""

                if degree or institution:

                    cursor.execute(
                        """
                        INSERT INTO education
                        (
                            resume_id,
                            degree,
                            institution,
                            year,
                            grade
                        )
                        VALUES
                        (%s, %s, %s, %s, %s)
                        """,
                        (
                            resume_id,
                            degree,
                            institution,
                            year,
                            grade
                        )
                    )

            # =================================================
            # SKILLS
            # =================================================

            skills = request.form.getlist("skill[]")

            for skill in skills:

                skill = skill.strip()

                if skill:

                    cursor.execute(
                        """
                        INSERT INTO skills
                        (
                            resume_id,
                            skill_name
                        )
                        VALUES
                        (%s, %s)
                        """,
                        (
                            resume_id,
                            skill
                        )
                    )

            # =================================================
            # PROJECTS
            # =================================================

            project_names = request.form.getlist(
                "project_name[]"
            )

            technologies = request.form.getlist(
                "technologies[]"
            )

            project_descriptions = request.form.getlist(
                "project_description[]"
            )

            for i in range(len(project_names)):

                project_name = (
                    project_names[i].strip()
                    if i < len(project_names)
                    else ""
                )

                technology = (
                    technologies[i].strip()
                    if i < len(technologies)
                    else ""
                )

                description = (
                    project_descriptions[i].strip()
                    if i < len(project_descriptions)
                    else ""
                )

                if project_name or technology or description:

                    cursor.execute(
                        """
                        INSERT INTO projects
                        (
                            resume_id,
                            project_name,
                            technologies,
                            description
                        )
                        VALUES
                        (%s, %s, %s, %s)
                        """,
                        (
                            resume_id,
                            project_name,
                            technology,
                            description
                        )
                    )

            # =================================================
            # EXPERIENCE
            # =================================================

            companies = request.form.getlist(
                "company[]"
            )

            positions = request.form.getlist(
                "position[]"
            )

            start_dates = request.form.getlist(
                "start_date[]"
            )

            end_dates = request.form.getlist(
                "end_date[]"
            )

            experience_descriptions = request.form.getlist(
                "experience_description[]"
            )

            for i in range(len(companies)):

                company = (
                    companies[i].strip()
                    if i < len(companies)
                    else ""
                )

                position = (
                    positions[i].strip()
                    if i < len(positions)
                    else ""
                )

                start_date = (
                    start_dates[i]
                    if i < len(start_dates)
                    else None
                )

                end_date = (
                    end_dates[i]
                    if i < len(end_dates)
                    else None
                )

                description = (
                    experience_descriptions[i].strip()
                    if i < len(experience_descriptions)
                    else ""
                )

                if (
                    company
                    or position
                    or start_date
                    or end_date
                    or description
                ):

                    if start_date == "":
                        start_date = None

                    if end_date == "":
                        end_date = None

                    duration = ""

                    if start_date and end_date:

                        duration = (
                            f"{start_date} to {end_date}"
                        )

                    elif start_date:

                        duration = (
                            f"{start_date} to Present"
                        )

                    cursor.execute(
                        """
                        INSERT INTO experience
                        (
                            resume_id,
                            company,
                            position,
                            duration,
                            description,
                            start_date,
                            end_date
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            resume_id,
                            company,
                            position,
                            duration,
                            description,
                            start_date,
                            end_date
                        )
                    )

            # =================================================
            # CERTIFICATIONS
            # =================================================

            certification_names = request.form.getlist(
                "certification_name[]"
            )

            issuers = request.form.getlist(
                "issuer[]"
            )

            certification_years = request.form.getlist(
                "certification_year[]"
            )

            for i in range(len(certification_names)):

                certification_name = (
                    certification_names[i].strip()
                    if i < len(certification_names)
                    else ""
                )

                issuer = (
                    issuers[i].strip()
                    if i < len(issuers)
                    else ""
                )

                certification_year = (
                    certification_years[i].strip()
                    if i < len(certification_years)
                    else ""
                )

                if certification_name or issuer:

                    cursor.execute(
                        """
                        INSERT INTO certifications
                        (
                            resume_id,
                            name,
                            issuer,
                            year
                        )
                        VALUES
                        (%s, %s, %s, %s)
                        """,
                        (
                            resume_id,
                            certification_name,
                            issuer,
                            certification_year
                        )
                    )

            # =================================================
            # COMMIT
            # =================================================

            connection.commit()

            return render_template(
                "resume_saved.html",
                resume_id=resume_id
            )

        except Exception as e:

            if connection:
                connection.rollback()

            return f"""
            <!DOCTYPE html>
            <html>

            <head>
                <title>Error Saving Resume</title>
            </head>

            <body>

                <h2>Error saving resume</h2>

                <p>{e}</p>

                <a href="/resume-builder">
                    Go Back
                </a>

            </body>

            </html>
            """

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "resume_builder.html",
        template_id=template_id
    )


# =========================================================
# USER - CHOOSE RESUME TEMPLATE
# =========================================================

@app.route("/templates")
def user_templates():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                template_id,
                template_name,
                description,
                template_type
            FROM resume_templates
            ORDER BY template_id ASC
            """
        )

        templates = cursor.fetchall()

        return render_template(
            "user_templates.html",
            templates=templates
        )

    except Exception as e:

        print("USER TEMPLATES ERROR:", e)

        return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>Template Error - ResumePro</title>

            <style>

                body {{
                    margin: 0;
                    background: #f5f7fb;
                    font-family: Arial, Helvetica, sans-serif;
                }}

                .error-box {{
                    max-width: 700px;
                    margin: 100px auto;
                    background: white;
                    padding: 40px;
                    border-radius: 18px;
                    text-align: center;
                    box-shadow:
                        0 10px 30px
                        rgba(0,0,0,0.10);
                }}

                h2 {{
                    color: #dc2626;
                }}

                .error {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #fef2f2;
                    color: #991b1b;
                    border-radius: 8px;
                    word-break: break-word;
                }}

                a {{
                    display: inline-block;
                    padding: 11px 20px;
                    background: #2563eb;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                }}

                a:hover {{
                    background: #1d4ed8;
                }}

            </style>

        </head>

        <body>

            <div class="error-box">

                <h2>
                    Error Loading Templates
                </h2>

                <div class="error">
                    {e}
                </div>

                <a href="/dashboard">
                    ← Back to Dashboard
                </a>

            </div>

        </body>

        </html>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# VIEW RESUME
# =========================================================

@app.route("/view-resume/<int:resume_id>")
def view_resume(resume_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                r.*,
                t.template_name,
                t.template_type
            FROM resumes r
            LEFT JOIN resume_templates t
                ON r.template_id = t.template_id
            WHERE r.resume_id = %s
            AND r.user_id = %s
            """,
            (
                resume_id,
                session["user_id"]
            )
        )

        resume = cursor.fetchone()

        if not resume:

            return """
            <h2>Resume not found.</h2>
            <a href="/dashboard">
                Back to Dashboard
            </a>
            """

        cursor.execute(
            """
            SELECT *
            FROM education
            WHERE resume_id = %s
            ORDER BY education_id ASC
            """,
            (resume_id,)
        )

        education = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM skills
            WHERE resume_id = %s
            ORDER BY skill_id ASC
            """,
            (resume_id,)
        )

        skills = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM projects
            WHERE resume_id = %s
            ORDER BY project_id ASC
            """,
            (resume_id,)
        )

        projects = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM experience
            WHERE resume_id = %s
            ORDER BY experience_id ASC
            """,
            (resume_id,)
        )

        experience = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM certifications
            WHERE resume_id = %s
            ORDER BY certification_id ASC
            """,
            (resume_id,)
        )

        certifications = cursor.fetchall()

        return render_template(
            "view_resume.html",
            resume=resume,
            education=education,
            skills=skills,
            projects=projects,
            experience=experience,
            certifications=certifications
        )

    except Exception as e:

        return f"""
        <h2>Error loading resume</h2>
        <p>{e}</p>
        <a href="/dashboard">
            Go Back
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# DELETE RESUME
# =========================================================

@app.route("/delete-resume/<int:resume_id>")
def delete_resume(resume_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM resumes
            WHERE resume_id = %s
            AND user_id = %s
            """,
            (
                resume_id,
                session["user_id"]
            )
        )

        connection.commit()

        return redirect(url_for("my_resumes"))

    except Exception as e:

        if connection:
            connection.rollback()

        return f"""
        <h2>Error deleting resume</h2>
        <p>{e}</p>
        <a href="/dashboard">
            Go Back
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# MY RESUMES
# =========================================================

@app.route("/my-resumes")
def my_resumes():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                r.resume_id,
                r.full_name,
                r.email,
                r.created_at,
                r.updated_at,
                r.template_id,
                t.template_name,
                t.template_type
            FROM resumes r
            LEFT JOIN resume_templates t
                ON r.template_id = t.template_id
            WHERE r.user_id = %s
            ORDER BY r.updated_at DESC
            """,
            (session["user_id"],)
        )

        resumes = cursor.fetchall()

        return render_template(
            "my_resumes.html",
            resumes=resumes
        )

    except Exception as e:

        return f"""
        <h2>Error loading resumes</h2>
        <p>{e}</p>
        <a href="/dashboard">
            Go Back
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# ATS CHECKER
# =========================================================

@app.route("/ats-checker", methods=["GET", "POST"])
def ats_checker():

    if "user_id" not in session:
        return redirect(url_for("login"))

    score = 0
    ats_score = 0

    message = None
    error = None

    missing_sections = []
    suggestions = []

    matched_keywords = []
    missing_keywords = []

    resume = None
    education = []
    skills = []
    projects = []
    experience = []
    certifications = []
    resumes = []

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # =====================================================
        # GET USER RESUMES
        # =====================================================

        cursor.execute(
            """
            SELECT
                resume_id,
                full_name,
                created_at
            FROM resumes
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (session["user_id"],)
        )

        resumes = cursor.fetchall()

        # =====================================================
        # NO RESUME
        # =====================================================

        if not resumes:

            message = "You have not created any resume yet."

            return render_template(
                "ats_checker.html",
                resumes=resumes,
                score=0,
                ats_score=0,
                message=message,
                error=None,
                missing_sections=[],
                suggestions=[],
                matched_keywords=[],
                missing_keywords=[],
                resume=None,
                education=[],
                skills=[],
                projects=[],
                experience=[],
                certifications=[]
            )

        # =====================================================
        # SELECT RESUME
        # =====================================================

        resume_id = request.form.get("resume_id")

        if resume_id:

            try:
                resume_id = int(resume_id)

            except (TypeError, ValueError):
                resume_id = None

        if not resume_id:
            resume_id = resumes[0]["resume_id"]

        # =====================================================
        # GET SELECTED RESUME
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM resumes
            WHERE resume_id = %s
            AND user_id = %s
            """,
            (
                resume_id,
                session["user_id"]
            )
        )

        resume = cursor.fetchone()

        if not resume:

            message = "The selected resume was not found."

            return render_template(
                "ats_checker.html",
                resumes=resumes,
                score=0,
                ats_score=0,
                message=message,
                error=None,
                missing_sections=[],
                suggestions=[],
                matched_keywords=[],
                missing_keywords=[],
                resume=None,
                education=[],
                skills=[],
                projects=[],
                experience=[],
                certifications=[]
            )

        # =====================================================
        # EDUCATION
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM education
            WHERE resume_id = %s
            ORDER BY education_id ASC
            """,
            (resume_id,)
        )

        education = cursor.fetchall()

        # =====================================================
        # SKILLS
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM skills
            WHERE resume_id = %s
            ORDER BY skill_id ASC
            """,
            (resume_id,)
        )

        skills = cursor.fetchall()

        # =====================================================
        # PROJECTS
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM projects
            WHERE resume_id = %s
            ORDER BY project_id ASC
            """,
            (resume_id,)
        )

        projects = cursor.fetchall()

        # =====================================================
        # EXPERIENCE
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM experience
            WHERE resume_id = %s
            ORDER BY experience_id ASC
            """,
            (resume_id,)
        )

        experience = cursor.fetchall()

        # =====================================================
        # CERTIFICATIONS
        # =====================================================

        cursor.execute(
            """
            SELECT *
            FROM certifications
            WHERE resume_id = %s
            ORDER BY certification_id ASC
            """,
            (resume_id,)
        )

        certifications = cursor.fetchall()

        # =====================================================
        # BUILD COMPLETE RESUME TEXT
        # =====================================================

        resume_text_parts = []

        # -----------------------------------------------------
        # PERSONAL INFORMATION
        # -----------------------------------------------------

        personal_fields = [
            "full_name",
            "email",
            "phone",
            "city",
            "state",
            "country",
            "linkedin",
            "github",
            "career_objective"
        ]

        for field in personal_fields:

            value = resume.get(field)

            if value:
                resume_text_parts.append(str(value))

        # -----------------------------------------------------
        # EDUCATION
        # -----------------------------------------------------

        for item in education:

            for field in [
                "degree",
                "institution",
                "year",
                "grade"
            ]:

                value = item.get(field)

                if value:
                    resume_text_parts.append(str(value))

        # -----------------------------------------------------
        # SKILLS
        # -----------------------------------------------------

        for item in skills:

            value = item.get("skill_name")

            if value:
                resume_text_parts.append(str(value))

        # -----------------------------------------------------
        # PROJECTS
        # -----------------------------------------------------

        for item in projects:

            for field in [
                "project_name",
                "technologies",
                "description"
            ]:

                value = item.get(field)

                if value:
                    resume_text_parts.append(str(value))

        # -----------------------------------------------------
        # EXPERIENCE
        # -----------------------------------------------------

        for item in experience:

            for field in [
                "company",
                "position",
                "duration",
                "description"
            ]:

                value = item.get(field)

                if value:
                    resume_text_parts.append(str(value))

        # -----------------------------------------------------
        # CERTIFICATIONS
        # -----------------------------------------------------

        for item in certifications:

            for field in [
                "name",
                "issuer",
                "year"
            ]:

                value = item.get(field)

                if value:
                    resume_text_parts.append(str(value))

        # =====================================================
        # COMPLETE RESUME TEXT
        # =====================================================

        resume_text = " ".join(resume_text_parts)
        resume_text = resume_text.lower()

        # =====================================================
        # GET KEYWORDS FROM ADMIN TABLE
        # IMPORTANT: TABLE = ats_keywords
        # =====================================================

        cursor.execute(
            """
            SELECT
                keyword_id,
                keyword,
                category
            FROM ats_keywords
            WHERE keyword IS NOT NULL
            AND TRIM(keyword) <> ''
            ORDER BY keyword ASC
            """
        )

        admin_keywords = cursor.fetchall()

        # =====================================================
        # CHECK ADMIN KEYWORDS AGAINST RESUME
        # =====================================================

        valid_keywords = []

        for item in admin_keywords:

            keyword = item.get("keyword")

            if not keyword:
                continue

            keyword_clean = str(keyword).strip()

            if not keyword_clean:
                continue

            valid_keywords.append(item)

            keyword_lower = keyword_clean.lower()

            # Word/phrase matching
            pattern = (
                r"(?<!\w)"
                + re.escape(keyword_lower)
                + r"(?!\w)"
            )

            if re.search(pattern, resume_text):

                matched_keywords.append({
                    "keyword": keyword_clean,
                    "category": item.get("category")
                })

            else:

                missing_keywords.append({
                    "keyword": keyword_clean,
                    "category": item.get("category")
                })

        # =====================================================
        # KEYWORD SCORE - 30 MARKS
        # =====================================================

        total_keywords = len(valid_keywords)
        matched_count = len(matched_keywords)

        if total_keywords > 0:

            keyword_score = round(
                (matched_count / total_keywords) * 30
            )

        else:

            keyword_score = 0

        ats_score += keyword_score

        # =====================================================
        # PERSONAL INFORMATION - 20 MARKS
        # =====================================================

        required_personal_fields = [
            "full_name",
            "email",
            "phone",
            "city",
            "state"
        ]

        filled_personal = 0

        for field in required_personal_fields:

            value = resume.get(field)

            if value and str(value).strip():
                filled_personal += 1

        personal_score = round(
            (filled_personal /
             len(required_personal_fields)) * 20
        )

        ats_score += personal_score

        # Missing personal information

        if not resume.get("full_name"):
            missing_sections.append("Full Name")

        if not resume.get("email"):
            missing_sections.append("Email")

        if not resume.get("phone"):
            missing_sections.append("Phone Number")

        if not resume.get("city"):
            missing_sections.append("City")

        if not resume.get("state"):
            missing_sections.append("State")

        # =====================================================
        # CAREER OBJECTIVE - 10 MARKS
        # =====================================================

        if resume.get("career_objective"):

            ats_score += 10

        else:

            missing_sections.append("Career Objective")

            suggestions.append(
                "Add a clear and relevant career objective."
            )

        # =====================================================
        # EDUCATION - 10 MARKS
        # =====================================================

        if education:

            ats_score += 10

        else:

            missing_sections.append("Education")

            suggestions.append(
                "Add your education details."
            )

        # =====================================================
        # SKILLS - 10 MARKS
        # =====================================================

        if skills:

            ats_score += 10

        else:

            missing_sections.append("Skills")

            suggestions.append(
                "Add relevant technical and professional skills."
            )

        # =====================================================
        # PROJECTS - 10 MARKS
        # =====================================================

        if projects:

            ats_score += 10

        else:

            missing_sections.append("Projects")

            suggestions.append(
                "Add at least one relevant project."
            )

        # =====================================================
        # EXPERIENCE - 5 MARKS
        # =====================================================

        if experience:

            ats_score += 5

        else:

            suggestions.append(
                "Add internship or work experience if available."
            )

        # =====================================================
        # CERTIFICATIONS - 5 MARKS
        # =====================================================

        if certifications:

            ats_score += 5

        else:

            suggestions.append(
                "Add relevant certifications if available."
            )

        # =====================================================
        # ADMIN KEYWORD SUGGESTIONS
        # =====================================================

        if missing_keywords:

            for item in missing_keywords[:10]:

                keyword = item["keyword"]
                category = item.get("category")

                if category:

                    suggestions.append(
                        f"Consider adding '{keyword}' "
                        f"under {category} if it is relevant "
                        f"to your profile."
                    )

                else:

                    suggestions.append(
                        f"Consider adding '{keyword}' "
                        f"if it is relevant to your profile."
                    )

        # =====================================================
        # NO ADMIN KEYWORDS
        # =====================================================

        if total_keywords == 0:

            suggestions.append(
                "No ATS keywords have been configured "
                "by the administrator yet."
            )

        # =====================================================
        # REMOVE DUPLICATE SUGGESTIONS
        # =====================================================

        suggestions = list(
            dict.fromkeys(suggestions)
        )

        # =====================================================
        # SCORE LIMIT
        # =====================================================

        if ats_score > 100:
            ats_score = 100

        if ats_score < 0:
            ats_score = 0

        score = ats_score

        # =====================================================
        # RENDER ATS CHECKER
        # =====================================================

        return render_template(
            "ats_checker.html",

            resumes=resumes,

            score=score,
            ats_score=ats_score,

            message=None,
            error=None,

            missing_sections=missing_sections,
            suggestions=suggestions,

            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,

            resume=resume,

            education=education,
            skills=skills,
            projects=projects,
            experience=experience,
            certifications=certifications
        )

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        print("======================================")
        print("ATS CHECKER ERROR:")
        print(e)
        print("======================================")

        return render_template(
            "ats_checker.html",

            resumes=resumes,

            score=0,
            ats_score=0,

            message=None,
            error=str(e),

            missing_sections=[],
            suggestions=[],

            matched_keywords=[],
            missing_keywords=[],

            resume=resume,

            education=education,
            skills=skills,
            projects=projects,
            experience=experience,
            certifications=certifications
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        if request.method == "POST":

            name = request.form.get("name")
            email = request.form.get("email")

            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE users
                SET name = %s,
                    email = %s
                WHERE user_id = %s
                """,
                (
                    name,
                    email,
                    session["user_id"]
                )
            )

            connection.commit()

            session["user_name"] = name
            session["user_email"] = email

            cursor.close()
            cursor = None

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                user_id,
                name,
                email
            FROM users
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        return render_template(
            "profile.html",
            user=user
        )

    except Exception as e:

        return f"""
        <h2>Profile Error</h2>
        <p>{e}</p>
        <a href="/dashboard">
            Go Back
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        admin_email = request.form.get("admin_email")
        admin_password = request.form.get("admin_password")

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    admin_id,
                    name,
                    email,
                    password
                FROM admin
                WHERE email = %s
                AND password = %s
                """,
                (
                    admin_email,
                    admin_password
                )
            )

            admin = cursor.fetchone()

            if admin:

                session["admin_id"] = admin["admin_id"]
                session["admin_name"] = admin["name"]
                session["admin_email"] = admin["email"]

                return redirect(
                    url_for("admin_dashboard")
                )

            else:

                return render_template(
                    "admin/admin_login.html",
                    error="Invalid admin email or password."
                )

        except Exception as e:

            print("====================================")
            print("ADMIN LOGIN ERROR:", e)
            print("====================================")

            return render_template(
                "admin/admin_login.html",
                error="Unable to process admin login. Please try again."
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "admin/admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            """
        )

        total_users = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM resumes
            """
        )

        total_resumes = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM resume_templates
            """
        )

        total_templates = cursor.fetchone()["total"]

        return render_template(
            "admin/admin_dashboard.html",
            total_users=total_users,
            total_resumes=total_resumes,
            total_templates=total_templates
        )

    except Exception as e:

        return f"""
        <h2>Admin Dashboard Error</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - MANAGE USERS
# =========================================================

@app.route("/admin/users")
def manage_users():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                user_id,
                name,
                email
            FROM users
            ORDER BY user_id DESC
            """
        )

        users = cursor.fetchall()

        return render_template(
            "admin/manage_users.html",
            users=users
        )

    except Exception as e:

        return f"""
        <h2>Error loading users</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - MANAGE RESUMES
# =========================================================

@app.route("/admin/resumes")
def manage_resumes():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                r.resume_id,
                r.full_name,
                r.email,
                r.created_at,
                u.name AS user_name,
                t.template_name
            FROM resumes r

            LEFT JOIN users u
                ON r.user_id = u.user_id

            LEFT JOIN resume_templates t
                ON r.template_id = t.template_id

            ORDER BY r.created_at DESC
            """
        )

        resumes = cursor.fetchall()

        return render_template(
            "admin/manage_resumes.html",
            resumes=resumes
        )

    except Exception as e:

        return f"""
        <h2>Error loading resumes</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - MANAGE TEMPLATES
# =========================================================

@app.route("/admin/templates")
def manage_templates():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                template_id,
                template_name,
                description,
                template_type,
                created_at
            FROM resume_templates
            ORDER BY template_id ASC
            """
        )

        templates = cursor.fetchall()

        return render_template(
            "admin/manage_templates.html",
            templates=templates
        )

    except Exception as e:

        return f"""
        <h2>Error loading templates</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - MANAGE ATS KEYWORDS
# =========================================================
# IMPORTANT:
# YOUR TABLE NAME IS ats_keywords
# =========================================================

@app.route("/admin/keywords", methods=["GET", "POST"])
def manage_keywords():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # =====================================================
        # ADD KEYWORD
        # =====================================================

        if request.method == "POST":

            keyword = request.form.get(
                "keyword",
                ""
            ).strip()

            category = request.form.get(
                "category",
                ""
            ).strip()

            # -------------------------------------------------
            # EMPTY KEYWORD
            # -------------------------------------------------

            if not keyword:

                cursor.execute(
                    """
                    SELECT
                        keyword_id,
                        keyword,
                        category,
                        created_at
                    FROM ats_keywords
                    ORDER BY keyword_id DESC
                    """
                )

                keywords = cursor.fetchall()

                return render_template(
                    "admin/manage_keywords.html",
                    keywords=keywords,
                    error="Please enter a keyword."
                )

            # -------------------------------------------------
            # CHECK DUPLICATE
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT keyword_id
                FROM ats_keywords
                WHERE LOWER(keyword) = LOWER(%s)
                LIMIT 1
                """,
                (keyword,)
            )

            existing_keyword = cursor.fetchone()

            if existing_keyword:

                cursor.execute(
                    """
                    SELECT
                        keyword_id,
                        keyword,
                        category,
                        created_at
                    FROM ats_keywords
                    ORDER BY keyword_id DESC
                    """
                )

                keywords = cursor.fetchall()

                return render_template(
                    "admin/manage_keywords.html",
                    keywords=keywords,
                    error="This keyword already exists."
                )

            # -------------------------------------------------
            # INSERT INTO ats_keywords
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO ats_keywords
                (
                    keyword,
                    category
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    keyword,
                    category if category else None
                )
            )

            connection.commit()

            return redirect(
                url_for("manage_keywords")
            )

        # =====================================================
        # GET ALL KEYWORDS
        # =====================================================

        cursor.execute(
            """
            SELECT
                keyword_id,
                keyword,
                category,
                created_at
            FROM ats_keywords
            ORDER BY keyword_id DESC
            """
        )

        keywords = cursor.fetchall()

        # =====================================================
        # DISPLAY
        # =====================================================

        return render_template(
            "admin/manage_keywords.html",
            keywords=keywords,
            error=None
        )

    except Exception as e:

        print("========================================")
        print("ADMIN KEYWORDS ERROR:")
        print(e)
        print("========================================")

        return render_template(
            "admin/manage_keywords.html",
            keywords=[],
            error=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()
# =========================================================
# ADMIN - REPORTS
# =========================================================

@app.route("/admin/reports")
def admin_reports():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # =================================================
        # TOTAL USERS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM users
        """)

        total_users = cursor.fetchone()["total"]


        # =================================================
        # TOTAL RESUMES
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM resumes
        """)

        total_resumes = cursor.fetchone()["total"]


        # =================================================
        # TOTAL EDUCATION RECORDS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM education
        """)

        total_education = cursor.fetchone()["total"]


        # =================================================
        # TOTAL SKILLS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM skills
        """)

        total_skills = cursor.fetchone()["total"]


        # =================================================
        # TOTAL PROJECTS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM projects
        """)

        total_projects = cursor.fetchone()["total"]


        # =================================================
        # TOTAL EXPERIENCE
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM experience
        """)

        total_experience = cursor.fetchone()["total"]


        # =================================================
        # TOTAL CERTIFICATIONS
        # =================================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM certifications
        """)

        total_certifications = cursor.fetchone()["total"]


        # =================================================
        # TOTAL ATS REPORTS
        # =================================================

        total_ats = 0

        try:

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM ats_reports
            """)

            result = cursor.fetchone()

            if result:
                total_ats = result["total"]

        except Exception as e:

            print("ATS REPORTS COUNT ERROR:", e)

            total_ats = 0


        # =================================================
        # TOTAL FEEDBACK
        # =================================================

        total_feedback = 0

        try:

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM feedback
            """)

            result = cursor.fetchone()

            if result:
                total_feedback = result["total"]

        except Exception as e:

            print("FEEDBACK COUNT ERROR:", e)

            total_feedback = 0


        # =================================================
        # MONTHLY RESUME DATA
        # =================================================

        monthly_resumes = []

        try:

            cursor.execute("""
                SELECT
                    DATE_FORMAT(created_at, '%Y-%m') AS month,
                    COUNT(*) AS resume_count
                FROM resumes
                GROUP BY DATE_FORMAT(created_at, '%Y-%m')
                ORDER BY month ASC
            """)

            monthly_resumes = cursor.fetchall()

        except Exception as e:

            print("MONTHLY RESUME REPORT ERROR:", e)

            monthly_resumes = []


        # =================================================
        # SEND DATA TO HTML
        # =================================================

        return render_template(
            "admin/reports.html",

            total_users=total_users,

            total_resumes=total_resumes,

            total_education=total_education,

            total_skills=total_skills,

            total_projects=total_projects,

            total_experience=total_experience,

            total_certifications=total_certifications,

            total_ats=total_ats,

            total_feedback=total_feedback,

            monthly_resumes=monthly_resumes
        )


    except Exception as e:

        print("ADMIN REPORTS ERROR:", e)

        return f"""
        <div style="
            font-family: Arial;
            padding: 40px;
        ">

            <h2>Admin Reports Error</h2>

            <p>{e}</p>

            <a href="{url_for('admin_dashboard')}">
                Back to Dashboard
            </a>

        </div>
        """


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN - FEEDBACK
# =========================================================

@app.route("/admin/feedback")
def admin_feedback():

    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SHOW TABLES LIKE 'feedback'
            """
        )

        table_exists = cursor.fetchone()

        feedback = []

        if table_exists:

            cursor.execute(
                """
                SELECT *
                FROM feedback
                ORDER BY 1 DESC
                """
            )

            feedback = cursor.fetchall()

        return render_template(
            "admin/feedback.html",
            feedback=feedback
        )

    except Exception as e:

        return f"""
        <h2>Feedback Error</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)

    return redirect(url_for("admin_login"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)