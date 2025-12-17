from flask import (
    Flask, render_template, request,
    redirect, session, make_response,
    render_template_string
)
import mysql.connector
import pdfkit
import os
import json
from config import DB_CONFIG, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

# -----------------------------
# PDF configuration
# -----------------------------
PDF_CONFIG = pdfkit.configuration(
    wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
)

# -----------------------------
# Database connection
# -----------------------------
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# -----------------------------
# Resume Form
# -----------------------------
@app.route('/', methods=['GET', 'POST'])
def resume_form():
    if request.method == 'POST':

        # ---------- Basic Info ----------
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        website = request.form.get('website')
        summary = request.form.get('summary')
        skills = request.form.get('skills')

        # ---------- Education ----------
        edu_degrees = request.form.getlist('edu_degree[]')
        edu_institutes = request.form.getlist('edu_institute[]')
        edu_years = request.form.getlist('edu_year[]')

        education = []
        for d, i, y in zip(edu_degrees, edu_institutes, edu_years):
            if d or i or y:
                education.append({
                    "degree": d,
                    "institute": i,
                    "year": y
                })

        # ---------- Experience ----------
        exp_jobs = request.form.getlist('exp_job[]')
        exp_companies = request.form.getlist('exp_company[]')
        exp_durations = request.form.getlist('exp_duration[]')
        exp_descs = request.form.getlist('exp_desc[]')

        experience = []
        for j, c, du, de in zip(exp_jobs, exp_companies, exp_durations, exp_descs):
            if j or c:
                experience.append({
                    "job": j,
                    "company": c,
                    "duration": du,
                    "description": de
                })

        # ---------- Languages ----------
        lang_names = request.form.getlist('lang_name[]')
        lang_levels = request.form.getlist('lang_level[]')

        languages = []
        for n, l in zip(lang_names, lang_levels):
            if n:
                languages.append({
                    "language": n,
                    "level": l
                })

        # ---------- Certifications ----------
        cert_names = request.form.getlist('cert_name[]')
        cert_orgs = request.form.getlist('cert_org[]')
        cert_years = request.form.getlist('cert_year[]')

        certifications = []
        for n, o, y in zip(cert_names, cert_orgs, cert_years):
            if n:
                certifications.append({
                    "name": n,
                    "organization": o,
                    "year": y
                })

        # ---------- Save to DB ----------
        con = get_db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO resumes
            (name, email, phone, address, website, summary, skills,
             education, experience, languages, certifications)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name, email, phone, address, website, summary, skills,
            json.dumps(education),
            json.dumps(experience),
            json.dumps(languages),
            json.dumps(certifications)
        ))

        con.commit()
        resume_id = cur.lastrowid
        cur.close()
        con.close()

        return redirect(f'/download/{resume_id}')

    return render_template('user/resume_form.html')
# -----------------------------
# Download Page
# -----------------------------
@app.route('/download/<int:id>')
def download(id):
    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            address,
            website,
            summary,
            skills,
            education,
            experience,
            languages,
            certifications
        FROM resumes
        WHERE id = %s
    """, (id,))

    resume = cur.fetchone()

    cur.close()
    con.close()

    if not resume:
        return "Resume not found", 404

    # ---------- Convert JSON fields ----------
    resume['education'] = json.loads(resume['education']) if resume['education'] else []
    resume['experience'] = json.loads(resume['experience']) if resume['experience'] else []
    resume['languages'] = json.loads(resume['languages']) if resume['languages'] else []
    resume['certifications'] = json.loads(resume['certifications']) if resume['certifications'] else []

    # ---------- Get template list ----------
    templates = os.listdir("static/templates_files")

    return render_template(
        'user/download.html',
        resume=resume,
        resume_id=id,
        templates=templates
    )

# -----------------------------
# User PDF Download
# -----------------------------

@app.route('/download-pdf/<int:id>')
def download_pdf(id):
    # ---------------------------
    # 1️⃣ Get selected template
    # ---------------------------
    template_file = request.args.get('template')

    if not template_file:
        return "Template not selected", 400

    template_path = os.path.join(
        "static/templates_files",
        os.path.basename(template_file)
    )

    if not os.path.exists(template_path):
        return "Template not found", 404

    # ---------------------------
    # 2️⃣ Fetch resume from DB
    # ---------------------------
    con = get_db()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT
            name,
            email,
            phone,
            address,
            website,
            summary,
            skills,
            education,
            experience,
            languages,
            certifications
        FROM resumes
        WHERE id = %s
    """, (id,))

    resume = cur.fetchone()
    cur.close()
    con.close()

    if not resume:
        return "Resume not found", 404

    # ---------------------------
    # 3️⃣ Convert JSON fields
    # ---------------------------
    resume['education'] = json.loads(resume['education']) if resume['education'] else []
    resume['experience'] = json.loads(resume['experience']) if resume['experience'] else []
    resume['languages'] = json.loads(resume['languages']) if resume['languages'] else []
    resume['certifications'] = json.loads(resume['certifications']) if resume['certifications'] else []

    # ---------------------------
    # 4️⃣ Load & render template
    # ---------------------------
    with open(template_path, encoding="utf-8") as f:
        html_template = f.read()

    rendered_html = render_template_string(
        html_template,
        resume=resume
    )

    # ---------------------------
    # 5️⃣ Generate PDF
    # ---------------------------
    pdf = pdfkit.from_string(
        rendered_html,
        False,
        configuration=PDF_CONFIG
    )

    # ---------------------------
    # 6️⃣ Return PDF response
    # ---------------------------
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename={resume["name"].replace(" ", "_")}_Resume.pdf'
    )

    return response

# -----------------------------
# Templates Route
# -----------------------------

@app.route('/template/<template_name>')
def preview_template(template_name):
    # Secure filename
    filename = f"{template_name}.html"

    template_path = os.path.join(
        'static',
        'templates_files',
        filename
    )

    if not os.path.exists(template_path):
        return "Template not found", 404

    with open(template_path, encoding='utf-8') as f:
        html = f.read()

    # Dummy preview data
    resume = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+91 98765 43210",
        "address": "Delhi, India",
        "website": "www.johndoe.com",
        "summary": "Passionate software developer with strong backend skills.",
        "skills": "Python, Flask, HTML, CSS, JavaScript",
        "education": [
            {"degree": "B.Tech", "institute": "ABC University", "year": "2019-2023"}
        ],
        "experience": [
            {
                "job": "Backend Developer",
                "company": "XYZ Pvt Ltd",
                "duration": "2023-Present",
                "description": "Worked on Flask APIs and MySQL"
            }
        ],
        "languages": [
            {"language": "English", "level": "Fluent"},
            {"language": "Hindi", "level": "Native"}
        ],
        "certifications": [
            {"name": "Python Developer", "organization": "Coursera", "year": "2023"}
        ]
    }

    return render_template_string(html, resume=resume)

# -----------------------------
# Admin Side
# -----------------------------

# -----------------------------
# Login Page
# -----------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # SIMPLE ADMIN CREDENTIALS (you can move to DB later)
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            return render_template('admin/login.html', error="Invalid credentials")

    return render_template('admin/login.html')

# -----------------------------
# Dashboard Page
# -----------------------------

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')

    return render_template('admin/dashboard.html')


# -----------------------------
# View Resume Page
# -----------------------------

@app.route('/admin/resumes')
def admin_resumes():
    if not session.get('admin'):
        return redirect('/admin/login')

    con = get_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM resumes ORDER BY id DESC")
    resumes = cur.fetchall()
    cur.close()
    con.close()

    # Convert JSON fields to Python objects
    for r in resumes:
        r['education'] = json.loads(r['education']) if r['education'] else []
        r['experience'] = json.loads(r['experience']) if r['experience'] else []

    return render_template('admin/resumes.html', resumes=resumes)



# -----------------------------
# View single Resume Page
# -----------------------------

@app.route('/admin/resume/<int:id>')
def admin_view_resume(id):
    if not session.get('admin'):
        return redirect('/admin/login')

    con = get_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM resumes WHERE id=%s", (id,))
    resume = cur.fetchone()
    cur.close()
    con.close()

    if not resume:
        return "Resume not found", 404

    resume['education'] = json.loads(resume['education'])
    resume['experience'] = json.loads(resume['experience'])
    resume['languages'] = json.loads(resume['languages'])
    resume['certifications'] = json.loads(resume['certifications'])

    return render_template(
        'admin/view_resume.html',
        resume=resume
    )

# -----------------------------
# Delete Resume Page
# -----------------------------

@app.route('/admin/delete/<int:id>')
def admin_delete_resume(id):
    if not session.get('admin'):
        return redirect('/admin/login')

    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM resumes WHERE id=%s", (id,))
    con.commit()
    cur.close()
    con.close()

    return redirect('/admin/resumes')

# -----------------------------
#  Manage Templates
# -----------------------------


TEMPLATE_DIR = "static/templates_files"

@app.route('/admin/templates')
def manage_templates():
    templates = []

    for file in os.listdir(TEMPLATE_DIR):
        if file.endswith('.html'):
            templates.append(file)

    return render_template(
        'admin/manage_templates.html',
        templates=templates
    )
    

# -----------------------------
#  Add Upload Template
# -----------------------------
    
@app.route('/admin/templates/upload', methods=['GET', 'POST'])
def upload_template():
    if request.method == 'POST':
        file = request.files['template']

        if file.filename.endswith('.html'):
            file.save(os.path.join(TEMPLATE_DIR, file.filename))

        return redirect('/admin/templates')

    return '''
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="template">
        <button>Upload</button>
    </form>
    '''


# -----------------------------
# Admin Logout  
# -----------------------------

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')




# -----------------------------
# Run App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
