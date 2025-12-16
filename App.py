from flask import (
    Flask, render_template, request,
    redirect, session, make_response,
    render_template_string
)
import mysql.connector
import pdfkit
import os
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
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        skills = request.form.get('skills')
        education = request.form.get('education')
        experience = request.form.get('experience')

        con = get_db()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO resumes (name, email, phone, skills, education, experience)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, phone, skills, education, experience))
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
    cur = con.cursor()
    cur.execute(
        "SELECT name, email, skills FROM resumes WHERE id=%s",
        (id,)
    )
    row = cur.fetchone()
    cur.close()
    con.close()

    if not row:
        return "Resume not found", 404

    resume = {
        "name": row[0],
        "email": row[1],
        "skills": row[2]
    }

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
    template_file = request.args.get('template')

    if not template_file:
        return "Template not selected", 400

    template_path = os.path.join(
        "static/templates_files",
        os.path.basename(template_file)
    )

    if not os.path.exists(template_path):
        return "Template not found", 404

    con = get_db()
    cur = con.cursor()
    cur.execute(
        "SELECT name, email, skills FROM resumes WHERE id=%s",
        (id,)
    )
    row = cur.fetchone()
    cur.close()
    con.close()

    if not row:
        return "Resume not found", 404

    resume = dict(zip(['name', 'email', 'skills'], row))

    with open(template_path, encoding="utf-8") as f:
        html = f.read()

    rendered_html = render_template_string(html, **resume)

    pdf = pdfkit.from_string(rendered_html, False, configuration=PDF_CONFIG)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=resume.pdf'
    return response

# -----------------------------
# Run App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
