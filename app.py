import os
import secrets
import sqlite3
import urllib.parse
from datetime import date, datetime, timezone
from functools import wraps
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for, send_from_directory
from jinja2 import DictLoader
from werkzeug.security import check_password_hash, generate_password_hash

# === CONFIG - Can be changed in Admin > School Settings ===
SCHOOL_NAME = "Lundi Primary School"
SCHOOL_MOTTO = "Knowledge - Integrity - Service"
SCHOOL_LOCATION = "Lundi, Midlands Province, Zimbabwe"
COMPANY_NAME = "TransitLink Technologies"
COMPANY_TAGLINE = "Connecting Schools, Empowering Futures"
COMPANY_EMAIL = "info@transitlink.co.zw"
COMPANY_WEBSITE = "www.transitlink.co.zw"

ROLES = ("admin", "teacher", "bursar", "parent", "student")
CURRENCIES = ("USD", "ZiG")
FEE_CATEGORIES = ("tuition", "sdc_levy", "exam_fee", "practical", "transport", "uniform", "stationery")
LEVELS = ("ECD A", "ECD B", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Form 1", "Form 2", "Form 3", "Form 4", "Form 5", "Form 6")
TERMS = ("Term 1", "Term 2", "Term 3")

def current_term():
    m = date.today().month
    return "Term 1" if m <= 4 else ("Term 2" if m <= 8 else "Term 3")
def current_year():
    return date.today().year

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lundi-primary-dev-secret-change-me")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lundi_v2.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png"}

def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def get_setting(key, default=""):
    try:
        c = get_db()
        r = c.execute("SELECT value FROM school_settings WHERE key=?", (key,)).fetchone()
        c.close()
        return r["value"] if r and r["value"] else default
    except Exception:
        return default

def school_name():
    return get_setting("school_name", SCHOOL_NAME)

def wa_link(phone, msg):
    p = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if p.startswith("0"):
        p = "263" + p[1:]
    if not p:
        return "#"
    return "https://wa.me/" + p + "?text=" + urllib.parse.quote(msg)

def gen_code(prefix):
    import random, string
    return prefix + "-" + str(current_year()) + "-" + "".join(random.choices(string.digits, k=3))

def gen_pass():
    import random, string
    return "Pass@" + "".join(random.choices(string.digits, k=4))

def ensure_col(table, col, ddl):
    c = get_db()
    cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})")]
    if col not in cols:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            c.commit()
        except Exception as e:
            print("migrate", e)
    c.close()

# === TEMPLATES ===
BASE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{% block title %}Portal{% endblock %} - {{ SCHOOL_NAME }}</title><style>
:root{--navy:#0a1f44;--navy-deep:#061530;--navy-light:#1a3a6e;--gold:#d4af37;--gold-light:#e8c66a;--bg:#f4f1e8;--card:#fff;--ink:#1f2937;--muted:#6b7280;--ok:#047857;--bad:#b91c1c;}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--ink);display:flex;flex-direction:column;min-height:100vh;}
header{background:linear-gradient(135deg,var(--navy-deep),var(--navy),var(--navy-light));border-bottom:3px solid var(--gold);color:#fff;padding:14px 22px;}
header .top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
header .name{font-weight:800;font-size:1.15rem;color:var(--gold-light)}header .motto{font-size:.78rem;opacity:.9;font-style:italic;color:#cbd5e1}
header nav{display:flex;gap:14px;align-items:center;font-size:.88rem;flex-wrap:wrap}header a{color:var(--gold-light);text-decoration:none}
main{flex:1;max-width:1200px;margin:22px auto;padding:0 16px 30px;width:100%}
.card{background:var(--card);border-radius:12px;padding:18px 20px;box-shadow:0 1px 3px rgba(10,31,68,.08);border-top:3px solid var(--gold);margin-bottom:20px;}
.card h2{margin:0 0 14px;font-size:1rem;color:var(--navy)}.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.stat-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;font-weight:600}.stat-value{font-size:1.55rem;font-weight:700;margin:.15rem 0;color:var(--navy)}
table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #eef1f6}th{color:var(--navy);font-weight:700;font-size:.72rem;text-transform:uppercase;background:#faf8f2}
input,select,button,textarea{font:inherit}input,select,textarea{padding:9px 10px;border:1px solid #d6dbe6;border-radius:8px;width:100%;background:#fff}
label.lbl{display:block;font-size:.75rem;color:var(--navy);font-weight:600;margin-bottom:4px}
button{background:var(--navy);color:var(--gold-light);border:1px solid var(--gold);border-radius:8px;padding:10px 18px;cursor:pointer;font-weight:600}button.gold{background:var(--gold);color:var(--navy)}
form.inline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end}
.flash{padding:11px 14px;border-radius:8px;margin-bottom:14px;font-size:.9rem;border-left:4px solid}.flash.error{background:#fee2e2;color:#991b1b}.flash.success{background:#d1fae5;color:#065f46}
.muted{color:var(--muted);font-size:.85rem}.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600}.pill.ok{background:#d1fae5;color:#065f46}.pill.bad{background:#fee2e2;color:#991b1b}.pill.warn{background:#fef3c7;color:#92400e}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;background:#eef1f6;color:var(--navy);font-size:.72rem;margin-right:4px;font-weight:600}
.login-wrap{max-width:440px;margin:6vh auto}.login-wrap h1{font-size:1.2rem;text-align:center;margin:0 0 4px;color:var(--navy)}.login-wrap .field{margin-bottom:12px}
.branding-block{display:flex;flex-direction:column;align-items:center;text-align:center;background:#0a1f44;padding:20px;border-radius:12px;margin-top:24px;border:2px solid var(--gold);}
.branding-block .brand-tag{font-size:.85rem;font-style:italic;color:#e8c66a;font-weight:600;margin-top:12px}.branding-block .brand-contact{font-size:.78rem;color:#cbd5e1;margin-top:4px}
footer{background:linear-gradient(135deg,var(--navy-deep),var(--navy));border-top:3px solid var(--gold);color:#cbd5e1;padding:22px 16px}.footer-inner{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;align-items:center;text-align:center;gap:12px}
</style></head><body><header><div class="top"><div><div class="name">🎓 {{ SCHOOL_NAME }}</div><div class="motto">{{ SCHOOL_MOTTO }} - {{ SCHOOL_LOCATION }}</div></div><nav>
{% if session.get('user_id') %}<span>{{ current_term }} {{ current_year }}</span><span>{{ session.get('full_name') }} - {{ session.get('role')|capitalize }}</span><a href="{{ url_for('change_password') }}">Change Password</a><a href="{{ url_for('logout') }}">Logout</a>{% else %}<a href="{{ url_for('login') }}">Login</a><a href="{{ url_for('public_register') }}">Apply Online / Register</a>{% endif %}</nav></div></header><main>
{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{% endwith %}
{% block content %}{% endblock %}</main><footer><div class="footer-inner"><div style="font-weight:bold;color:var(--gold-light)">TransitLink</div><div>{{ COMPANY_TAGLINE }}</div><div>{{ COMPANY_EMAIL }} | {{ COMPANY_WEBSITE }}</div></div></footer></body></html>"""

LOGIN_HTML = """{% extends 'base.html' %}{% block title %}Sign in{% endblock %}{% block content %}<div class="login-wrap card"><h1>{{ SCHOOL_NAME }}</h1><p class="muted" style="text-align:center">Staff - Student - Parent Portal</p><form method="post"><div class="field"><label>Username</label><input name="username" required autofocus></div><div class="field"><label>Password</label><input type="password" name="password" required></div><button type="submit" style="width:100%">Sign in</button></form><p class="muted" style="margin-top:16px;line-height:1.8"><strong>Demo accounts</strong><br>Admin: <code>admin / admin123</code> - Teacher: <code>teacher / teacher123</code><br>Bursar: <code>bursar / bursar123</code> - Parent: <code>parent1 / parent123</code> - Student: <code>student1 / student123</code><br><br>New student? <a href="{{ url_for('public_register') }}">Apply Online - Registration</a></p><div class="branding-block"><div class="brand-tag">{{ COMPANY_TAGLINE }}</div><div class="brand-contact">{{ COMPANY_EMAIL }} - {{ COMPANY_WEBSITE }}</div></div></div>{% endblock %}"""
# === PART 2: DASHBOARD TEMPLATES ===
ADMIN_HTML = """{% extends 'base.html' %}{% block title %}Admin{% endblock %}{% block content %}
<div class="card"><h2>Head's Office - {{ SCHOOL_NAME }}</h2><p class="muted">{{ current_term }} - {{ current_year }}</p><p><a href="{{ url_for('admin_applications') }}">View Online Applications ({{ pending_count }})</a> | <a href="{{ url_for('teacher_assignments') }}">Assignments</a> | <a href="{{ url_for('change_password') }}">Change Password</a></p></div>
<div class="grid"><div class="card"><div class="stat-label">Students</div><div class="stat-value">{{ counts.students }}</div></div><div class="card"><div class="stat-label">Teachers</div><div class="stat-value">{{ counts.teachers }}</div></div><div class="card"><div class="stat-label">Parents</div><div class="stat-value">{{ counts.parents }}</div></div></div>
<div class="grid">{% for cur in CURRENCIES %}{% set t = totals[cur] %}<div class="card"><h2>Fee position - {{ cur }}</h2><p class="muted">Billed {{ t.due_cents|money(cur) }} - Paid {{ t.paid_cents|money(cur) }}</p><p class="stat-value {{ 'bad' if t.balance_cents > 0 else 'ok' }}">Outstanding: {{ t.balance_cents|money(cur) }}</p></div>{% endfor %}</div>
<div class="grid">
<div class="card"><h2>School Settings - Any School Can Use This</h2><p class="muted">Change school name, motto, location, phone, email. Shows everywhere.</p><form method="post" action="{{ url_for('admin_settings') }}"><label class="lbl">School Name</label><input name="school_name" value="{{ SCHOOL_NAME }}"><label class="lbl" style="margin-top:8px">Motto</label><input name="motto" value="{{ SCHOOL_MOTTO }}"><label class="lbl" style="margin-top:8px">Location</label><input name="location" value="{{ SCHOOL_LOCATION }}"><label class="lbl" style="margin-top:8px">School Phone / WhatsApp</label><input name="phone" value="{{ SCHOOL_PHONE }}"><label class="lbl" style="margin-top:8px">School Email</label><input name="email" value="{{ SCHOOL_EMAIL }}"><button type="submit" style="margin-top:10px" class="gold">Save School Settings</button></form></div>
<div class="card"><h2>Link Student to Parent</h2><p class="muted">Parent will see this child on their dashboard.</p><form method="post" action="{{ url_for('admin_link_parent') }}" class="inline"><div><label class="lbl">Student</label><select name="student_id">{% for s in all_students %}<option value="{{ s.id }}">{{ s.full_name }} - {{ s.class_name }} - ID {{ s.id }}</option>{% endfor %}</select></div><div><label class="lbl">Parent</label><select name="parent_id">{% for p in all_parents %}<option value="{{ p.id }}">{{ p.full_name }} - {{ p.username }} - ID {{ p.id }}</option>{% endfor %}</select></div><div><button type="submit">Link Parent</button></div></form><p class="muted" style="margin-top:8px">Also use: Student Phone, Address, Next-of-Kin are saved at registration / approval.</p></div>
</div>
<div class="grid">
<div class="card"><h2>Add a user</h2><form method="post" action="{{ url_for('admin_add_user') }}" class="inline"><div><label class="lbl">Role</label><select name="role" required><option value="student">Student</option><option value="teacher">Teacher</option><option value="parent">Parent</option><option value="bursar">Bursar</option></select></div><div><label class="lbl">Username</label><input name="username" required></div><div><label class="lbl">Full name</label><input name="full_name" required></div><div><label class="lbl">Phone / WhatsApp</label><input name="phone" placeholder="0771234567"></div><div><label class="lbl">Password</label><input name="password" type="password" required></div><div><button type="submit">Create User</button></div></form></div>
<div class="card"><h2>Post announcement</h2><form method="post" action="{{ url_for('admin_post_announcement') }}"><label class="lbl">Title</label><input name="title" required><label class="lbl" style="margin-top:8px">Body</label><textarea name="body" rows="3" required></textarea><label class="lbl" style="margin-top:8px">Audience</label><select name="audience"><option value="all">Everyone</option><option value="staff">Staff</option><option value="parents">Parents</option><option value="students">Students</option></select><button type="submit" style="margin-top:10px">Post</button></form></div>
</div>
<div class="card"><h2>All System Users</h2><table><thead><tr><th>ID</th><th>Username</th><th>Name</th><th>Role</th><th>Phone</th></tr></thead><tbody>{% for u in users %}<tr><td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.full_name }}</td><td><span class="tag">{{ u.role }}</span></td><td>{{ u.phone or '' }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>All Students - Address / Next of Kin / Parent</h2><table><thead><tr><th>Student</th><th>Class</th><th>Admission</th><th>Phone</th><th>Address</th><th>Next of Kin</th><th>Parent</th></tr></thead><tbody>{% for s in all_students %}<tr><td>{{ s.full_name }}</td><td>{{ s.class_name }}</td><td>{{ s.admission_no }}</td><td>{{ s.phone or '' }}</td><td>{{ s.address or '' }} {{ s.town or '' }}</td><td>{{ s.nok_name or '' }} {{ s.nok_phone or '' }} ({{ s.nok_relation or '' }})</td><td>{{ s.parent_name or '' }}</td></tr>{% endfor %}</tbody></table></div>
{% endblock %}"""

TEACHER_HTML = """{% extends 'base.html' %}{% block title %}Teacher{% endblock %}{% block content %}
<div class="card"><h2>Welcome, {{ teacher.full_name if teacher else session.full_name }}</h2><p class="muted">Subject: {{ teacher.subject if teacher else '-' }} | <a href="{{ url_for('teacher_assignments') }}">Send Assignments via WhatsApp / Email</a> | <a href="{{ url_for('change_password') }}">Change Password</a></p></div>
<div class="grid"><div class="card"><h2>Record a grade</h2><form method="post" action="{{ url_for('teacher_add_grade') }}" class="inline"><div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div><div><label class="lbl">Subject</label><input name="subject" required></div><div><label class="lbl">Term</label><select name="term">{% for t in TERMS %}<option>{{ t }}</option>{% endfor %}</select></div><div><label class="lbl">Score</label><input name="score" type="number" min="0" max="100" required></div><input type="hidden" name="academic_year" value="{{ current_year }}"><div><button type="submit">Save</button></div></form></div>
<div class="card"><h2>Mark attendance</h2><form method="post" action="{{ url_for('teacher_mark_attendance') }}" class="inline"><div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div><div><label class="lbl">Date</label><input name="day" type="date" value="{{ date.today() }}" required></div><div><label class="lbl">Status</label><select name="status"><option value="present">Present</option><option value="absent">Absent</option><option value="late">Late</option></select></div><div><button type="submit">Save</button></div></form></div></div>
{% endblock %}"""

STUDENT_HTML = """{% extends 'base.html' %}{% block title %}Student{% endblock %}{% block content %}
<div class="card"><h2>{{ student.full_name }}</h2><p class="muted">Admission No: {{ student.admission_no }} - Class: {{ student.class_name }} - Level: {{ student.school_level or 'Primary' }}</p><p class="muted">Phone: {{ student.phone or '-' }} | Address: {{ student.address or '' }} {{ student.town or '' }} | Next of Kin: {{ student.nok_name or '' }} {{ student.nok_phone or '' }}</p></div>
<div class="grid">{% for cur, f in fees.items() %}<div class="card"><h2>Fee balance - {{ cur }}</h2><p class="stat-value {{ 'bad' if f.balance_cents > 0 else 'ok' }}">{{ f.balance_cents|money(cur) }}</p></div>{% endfor %}</div>
<div class="card"><h2>My Grades</h2><table><thead><tr><th>Subject</th><th>Term</th><th>Score</th></tr></thead><tbody>{% for g in grades %}<tr><td>{{ g.subject }}</td><td>{{ g.term }}</td><td>{{ g.score }}</td></tr>{% endfor %}</tbody></table></div>
<div class="card"><h2>Announcements</h2>{% for a in announcements %}<p><b>{{ a.title }}</b><br>{{ a.body }}</p>{% endfor %}</div>
{% endblock %}"""

PARENT_HTML = """{% extends 'base.html' %}{% block title %}Parent{% endblock %}{% block content %}
<div class="card"><h2>Welcome, {{ parent.full_name if parent else session.full_name }}</h2><p class="muted">Your children linked to you</p></div>
{% for ch in children %}<div class="card"><h2>{{ ch.full_name }} - {{ ch.class_name }}</h2><p class="muted">Admission: {{ ch.admission_no }} | Address: {{ ch.address or '' }} | NOK: {{ ch.nok_name or '' }} {{ ch.nok_phone or '' }}</p>{% for cur, f in ch.fees.items() %}<p>Balance {{ cur }}: <b>{{ f.balance_cents|money(cur) }}</b></p>{% endfor %}<h3>Grades</h3><table><thead><tr><th>Subject</th><th>Term</th><th>Score</th></tr></thead><tbody>{% for g in ch.grades %}<tr><td>{{ g.subject }}</td><td>{{ g.term }}</td><td>{{ g.score }}</td></tr>{% endfor %}</tbody></table></div>{% else %}<div class="card"><p class="muted">No child linked yet. Ask Admin to link your child in Admin - Link Student to Parent.</p></div>{% endfor %}
<div class="card"><h2>Announcements</h2>{% for a in announcements %}<p><b>{{ a.title }}</b><br>{{ a.body }}</p>{% endfor %}</div>
{% endblock %}"""

BURSAR_HTML = """{% extends 'base.html' %}{% block title %}Bursar{% endblock %}{% block content %}
<div class="card"><h2>Bursar - {{ SCHOOL_NAME }}</h2></div><div class="grid">{% for cur in CURRENCIES %}{% set t = totals[cur] %}<div class="card"><h2>{{ cur }}</h2><p>Billed {{ t.due_cents|money(cur) }} - Paid {{ t.paid_cents|money(cur) }}</p><p class="stat-value">Outstanding: {{ t.balance_cents|money(cur) }}</p></div>{% endfor %}</div>
<div class="card"><h2>Record Payment</h2><form method="post" action="{{ url_for('bursar_add_payment') }}" class="inline"><div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div><div><label class="lbl">Amount</label><input name="amount" type="number" step="0.01" required></div><div><label class="lbl">Currency</label><select name="currency">{% for c in CURRENCIES %}<option>{{ c }}</option>{% endfor %}</select></div><div><label class="lbl">Method</label><select name="method"><option>Cash</option><option>EcoCash</option><option>Bank Transfer</option><option>Card</option></select></div><div><button type="submit">Save Payment</button></div></form></div>
<div class="card"><h2>Assign Fee</h2><form method="post" action="{{ url_for('bursar_add_fee') }}" class="inline"><div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div><div><label class="lbl">Category</label><select name="category">{% for c in FEE_CATEGORIES %}<option>{{ c }}</option>{% endfor %}</select></div><div><label class="lbl">Amount</label><input name="amount" type="number" step="0.01" required></div><div><label class="lbl">Currency</label><select name="currency">{% for c in CURRENCIES %}<option>{{ c }}</option>{% endfor %}</select></div><div><label class="lbl">Term</label><select name="term">{% for t in TERMS %}<option>{{ t }}</option>{% endfor %}</select></div><div><button type="submit">Assign Fee</button></div></form></div>
{% endblock %}"""

REGISTER_HTML = """{% extends 'base.html' %}{% block title %}Register{% endblock %}{% block content %}<div class="card"><h2>Online Registration - {{ SCHOOL_NAME }}</h2><p class="muted">Primary & Secondary - Fill all sections</p><form method="post" enctype="multipart/form-data"><h3>1. Learner</h3><input name="first_name" placeholder="First Name" required><br><br><input name="surname" placeholder="Surname" required><br><br><input name="dob" type="date" required><br><br><select name="gender"><option>Male</option><option>Female</option></select><br><br><select name="school_level" required><option>Primary</option><option>Secondary</option></select><br><br><input name="grade_applying" placeholder="Grade / Form Applying For e.g. Grade 5 / Form 1" required><br><br><input name="prev_school" placeholder="Previous School"><br><br><input name="birth_cert_no" placeholder="Birth Certificate No"><h3>2. Address</h3><input name="address" placeholder="House No, Street, Suburb"><br><br><input name="town" placeholder="Town / City"><h3>3. Parent / Guardian</h3><input name="parent_name" placeholder="Parent Full Name" required><br><br><input name="parent_relation" placeholder="Relationship Mother / Father / Guardian"><br><br><input name="parent_phone" placeholder="Parent Phone / WhatsApp e.g. 0771234567" required><br><br><input name="parent_email" placeholder="Parent Email"><br><br><input name="parent2_name" placeholder="Second Parent (optional)"><br><br><input name="parent2_phone" placeholder="Second Parent Phone"><h3>4. Next of Kin (if different)</h3><input name="nok_name" placeholder="Next of Kin Name"><br><br><input name="nok_phone" placeholder="Next of Kin Phone"><br><br><input name="nok_relation" placeholder="Relationship"><br><br><input name="nok_address" placeholder="Next of Kin Address"><h3>5. Documents (PDF / Photo)</h3><label class="lbl">Birth Certificate</label><input type="file" name="birth_cert"><label class="lbl">Results Slip / Report</label><input type="file" name="results"><label class="lbl">Parent ID</label><input type="file" name="parent_id"><button style="margin-top:12px" class="gold">Submit Application</button></form></div>{% endblock %}"""

CHANGE_HTML = """{% extends 'base.html' %}{% block title %}Change Password{% endblock %}{% block content %}<div class="card"><h2>Change Password</h2><p class="muted">If you logged in with a temporary password, you must change it now.</p><form method="post"><label class="lbl">New Password (6+ chars)</label><input type="password" name="new_password" required><button style="margin-top:10px">Change Password</button></form></div>{% endblock %}"""

APPLICATIONS_HTML = """{% extends 'base.html' %}{% block title %}Applications{% endblock %}{% block content %}<div class="card"><h2>Online Applications</h2>{% for a in apps %}<div style="border:1px solid #eee;padding:12px;margin:10px 0;border-radius:8px"><b>{{ a.first_name }} {{ a.surname }}</b> - {{ a.school_level }} {{ a.grade_applying }} - {{ a.town }} - Status: <b>{{ a.status }}</b><br>Learner DOB: {{ a.dob }} | Birth Cert: {{ a.birth_cert_no }} | Prev School: {{ a.prev_school }}<br>Address: {{ a.address }}<br>Parent: {{ a.parent_name }} ({{ a.parent_relation }}) - {{ a.parent_phone }} - {{ a.parent_email }} | 2nd Parent: {{ a.parent2_name }} {{ a.parent2_phone }}<br>NOK: {{ a.nok_name }} {{ a.nok_phone }} ({{ a.nok_relation }}) - {{ a.nok_address }}<br>Docs: {% if a.birth_cert_file %}<a href="{{ url_for('uploaded_file', fn=a.birth_cert_file) }}">Birth Cert</a>{% endif %} {% if a.results_file %}<a href="{{ url_for('uploaded_file', fn=a.results_file) }}">Results</a>{% endif %} {% if a.parent_id_file %}<a href="{{ url_for('uploaded_file', fn=a.parent_id_file) }}">Parent ID</a>{% endif %}<br>{% if a.status == 'approved' %}<p style="background:#d1fae5;padding:8px">Student: {{ a.temp_student_user }} / {{ a.temp_student_pass }} | Parent: {{ a.temp_parent_user }} / {{ a.temp_parent_pass }} | Student Code: {{ a.student_code }}</p><a target="_blank" href="https://wa.me/{{ a.parent_phone }}?text={{ ('Hello ' + a.parent_name + ', ' + a.first_name + ' accepted at ' + SCHOOL_NAME + '. Student ID ' + a.student_code + ' Username ' + a.temp_student_user + ' Password ' + a.temp_student_pass + '. Parent Username ' + a.temp_parent_user + ' Password ' + a.temp_parent_pass + '. Please change password after login.')|urlencode }}">Send via WhatsApp</a> | <a href="mailto:{{ a.parent_email }}?subject=Admission {{ SCHOOL_NAME }}&body=Student {{ a.temp_student_user }} {{ a.temp_student_pass }} Parent {{ a.temp_parent_user }} {{ a.temp_parent_pass }}">Send via Email</a>{% else %}<form method="post" action="{{ url_for('approve_application', aid=a.id) }}" style="display:inline"><button>Approve & Create IDs</button></form> <form method="post" action="{{ url_for('reject_application', aid=a.id) }}" style="display:inline"><button>Reject</button></form>{% endif %}</div>{% else %}<p class="muted">No applications yet. Share link: /register</p>{% endfor %}</div>{% endblock %}"""

ASSIGNMENTS_HTML = """{% extends 'base.html' %}{% block title %}Assignments{% endblock %}{% block content %}<div class="card"><h2>Teacher - Assignments / Homework</h2><form method="post" enctype="multipart/form-data"><input name="title" placeholder="Title e.g. Maths Homework" required><br><br><input name="subject" placeholder="Subject"><br><br><input name="class_name" placeholder="Class e.g. Grade 5 / Form 2"><br><br><input name="due_date" type="date"><br><br><textarea name="details" placeholder="Details"></textarea><br><br><input type="file" name="file"><button style="margin-top:10px">Create Assignment</button></form></div><div class="card"><h2>Send Assignment to Parents / Students</h2>{% for st in students %}<div style="padding:8px;border-bottom:1px solid #eee">{{ st.full_name }} - {{ st.class_name }} - Parent {{ st.parent_phone or '' }} {% if st.parent_phone %}<a target="_blank" href="https://wa.me/{{ st.parent_phone }}?text={{ ('Hello, ' + SCHOOL_NAME + ' Homework: Please check portal for new assignment.')|urlencode }}">WhatsApp Parent</a>{% endif %} {% if st.parent_email %}<a href="mailto:{{ st.parent_email }}?subject=Homework {{ SCHOOL_NAME }}">Email Parent</a>{% endif %}</div>{% endfor %}</div>{% for a in assigns %}<div class="card"><b>{{ a.title }}</b> {{ a.subject }} {{ a.class_name }} Due {{ a.due_date }}<br>{{ a.details }} {% if a.file_name %}<a href="{{ url_for('uploaded_file', fn=a.file_name) }}">Download File</a>{% endif %}</div>{% endfor %}{% endblock %}"""

templates = {"base.html": BASE_HTML, "login.html": LOGIN_HTML, "admin.html": ADMIN_HTML, "teacher.html": TEACHER_HTML, "student.html": STUDENT_HTML, "parent.html": PARENT_HTML, "bursar.html": BURSAR_HTML, "register.html": REGISTER_HTML, "change_password.html": CHANGE_HTML, "applications.html": APPLICATIONS_HTML, "assignments.html": ASSIGNMENTS_HTML}
app.jinja_loader = DictLoader(templates)

@app.template_filter("money")
def money_filter(cents, cur):
    try:
        v = (cents or 0) / 100
    except Exception:
        v = 0
    return f"{cur} {v:,.2f}"

@app.context_processor
def inject_globals():
    return {"SCHOOL_NAME": school_name(), "SCHOOL_MOTTO": get_setting("motto", SCHOOL_MOTTO), "SCHOOL_LOCATION": get_setting("location", SCHOOL_LOCATION), "SCHOOL_PHONE": get_setting("phone", ""), "SCHOOL_EMAIL": get_setting("email", COMPANY_EMAIL), "COMPANY_TAGLINE": COMPANY_TAGLINE, "COMPANY_EMAIL": COMPANY_EMAIL, "COMPANY_WEBSITE": COMPANY_WEBSITE, "CURRENCIES": CURRENCIES, "FEE_CATEGORIES": FEE_CATEGORIES, "TERMS": TERMS, "LEVELS": LEVELS, "current_term": current_term(), "current_year": current_year(), "date": date}

def migrate_v2():
    for t, col, ddl in [("users","phone","TEXT"),("users","must_change_password","INTEGER DEFAULT 0"),("students","phone","TEXT"),("students","address","TEXT"),("students","town","TEXT"),("students","parent_phone","TEXT"),("students","parent_email","TEXT"),("students","nok_name","TEXT"),("students","nok_phone","TEXT"),("students","nok_relation","TEXT"),("students","nok_address","TEXT"),("students","school_level","TEXT DEFAULT 'Primary'"),("students","grade_applying","TEXT"),("students","prev_school","TEXT"),("students","birth_cert_no","TEXT"),("students","student_code","TEXT")]:
        ensure_col(t, col, ddl)
    c = get_db()
    c.execute("CREATE TABLE IF NOT EXISTS school_settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, surname TEXT, dob TEXT, gender TEXT, school_level TEXT, grade_applying TEXT, prev_school TEXT, birth_cert_no TEXT, address TEXT, town TEXT, parent_name TEXT, parent_relation TEXT, parent_phone TEXT, parent_email TEXT, parent2_name TEXT, parent2_phone TEXT, nok_name TEXT, nok_phone TEXT, nok_relation TEXT, nok_address TEXT, birth_cert_file TEXT, results_file TEXT, parent_id_file TEXT, status TEXT DEFAULT 'pending', created_at TEXT, student_code TEXT, parent_code TEXT, temp_student_user TEXT, temp_student_pass TEXT, temp_parent_user TEXT, temp_parent_pass TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, teacher_id INTEGER, title TEXT, subject TEXT, class_name TEXT, due_date TEXT, details TEXT, file_name TEXT, created_at TEXT)")
    c.execute("INSERT OR IGNORE INTO school_settings(key,value) VALUES('school_name',?)", (SCHOOL_NAME,))
    c.execute("INSERT OR IGNORE INTO school_settings(key,value) VALUES('motto',?)", (SCHOOL_MOTTO,))
    c.execute("INSERT OR IGNORE INTO school_settings(key,value) VALUES('location',?)", (SCHOOL_LOCATION,))
    c.commit(); c.close()

def init_db():
    migrate_v2()
    c = get_db()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, full_name TEXT, role TEXT, phone TEXT, must_change_password INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, full_name TEXT, subject TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, parent_id INTEGER, full_name TEXT, admission_no TEXT, class_name TEXT, phone TEXT, address TEXT, town TEXT, parent_phone TEXT, parent_email TEXT, nok_name TEXT, nok_phone TEXT, nok_relation TEXT, nok_address TEXT, school_level TEXT, grade_applying TEXT, prev_school TEXT, birth_cert_no TEXT, student_code TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS fees (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, category TEXT, amount_cents INTEGER, currency TEXT, term TEXT, academic_year INTEGER, paid_cents INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, amount_cents INTEGER, currency TEXT, method TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS grades (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, teacher_id INTEGER, subject TEXT, term TEXT, academic_year INTEGER, score REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, day TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, audience TEXT, created_at TEXT)")
    if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)", ("admin", generate_password_hash("admin123"), "Administrator", "admin"))
        c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)", ("teacher", generate_password_hash("teacher123"), "Mr. Teacher", "teacher"))
        c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)", ("bursar", generate_password_hash("bursar123"), "Mrs. Bursar", "bursar"))
        c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)", ("parent1", generate_password_hash("parent123"), "Parent One", "parent"))
        c.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)", ("student1", generate_password_hash("student123"), "Student One", "student"))
        tid = c.execute("SELECT id FROM users WHERE username='teacher'").fetchone()["id"]
        c.execute("INSERT INTO teachers(user_id,full_name,subject) VALUES(?,?,?)", (tid, "Mr. Teacher", "Mathematics"))
        pid = c.execute("SELECT id FROM users WHERE username='parent1'").fetchone()["id"]
        sid = c.execute("SELECT id FROM users WHERE username='student1'").fetchone()["id"]
        c.execute("INSERT INTO students(user_id,parent_id,full_name,admission_no,class_name) VALUES(?,?,?,?,?)", (sid, pid, "Student One", "STU-2026-001", "Grade 5"))
    c.commit(); c.close()

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return w
# === PART 3: AUTH + DASHBOARD + V2 ROUTES ===
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        c = get_db()
        u = c.execute("SELECT * FROM users WHERE username=?", (request.form.get("username"),)).fetchone()
        c.close()
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session["user_id"] = u["id"]
            session["full_name"] = u["full_name"]
            session["role"] = u["role"]
            if u["must_change_password"]:
                return redirect(url_for("change_password"))
            return redirect(url_for("dashboard"))
        flash("Wrong username or password", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        np = request.form.get("new_password", "")
        if len(np) < 6:
            flash("Password must be 6+ characters", "error")
            return redirect(url_for("change_password"))
        c = get_db()
        c.execute("UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?", (generate_password_hash(np), session["user_id"]))
        c.commit(); c.close()
        flash("Password changed!", "success")
        return redirect(url_for("dashboard"))
    return render_template("change_password.html")

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    c = get_db()
    if role == "admin":
        counts = {"students": c.execute("SELECT COUNT(*) FROM students").fetchone()[0], "teachers": c.execute("SELECT COUNT(*) FROM users WHERE role='teacher'").fetchone()[0], "parents": c.execute("SELECT COUNT(*) FROM users WHERE role='parent'").fetchone()[0]}
        totals = {}
        for cur in CURRENCIES:
            due = c.execute("SELECT COALESCE(SUM(amount_cents),0) FROM fees WHERE currency=?", (cur,)).fetchone()[0]
            paid = c.execute("SELECT COALESCE(SUM(paid_cents),0) FROM fees WHERE currency=?", (cur,)).fetchone()[0]
            totals[cur] = {"due_cents": due, "paid_cents": paid, "balance_cents": due - paid}
        users = c.execute("SELECT * FROM users ORDER BY role, full_name").fetchall()
        all_students = c.execute("SELECT * FROM students ORDER BY full_name").fetchall()
        all_parents = c.execute("SELECT * FROM users WHERE role='parent' ORDER BY full_name").fetchall()
        pending = c.execute("SELECT COUNT(*) FROM applications WHERE status='pending'").fetchone()[0]
        c.close()
        return render_template("admin.html", counts=counts, totals=totals, users=users, all_students=all_students, all_parents=all_parents, pending_count=pending)
    if role == "teacher":
        tid = session["user_id"]
        teacher = c.execute("SELECT * FROM teachers WHERE user_id=?", (tid,)).fetchone()
        students = c.execute("SELECT * FROM students ORDER BY full_name").fetchall()
        c.close()
        return render_template("teacher.html", teacher=teacher, students=students)
    if role == "student":
        st = c.execute("SELECT * FROM students WHERE user_id=?", (session["user_id"],)).fetchone()
        if not st:
            c.close()
            flash("No student record linked", "error")
            return render_template("student.html", student={"full_name": session["full_name"], "admission_no": "-", "class_name": "-"}, fees={}, grades=[], announcements=[])
        fees = {}
        for cur in CURRENCIES:
            due = c.execute("SELECT COALESCE(SUM(amount_cents),0) FROM fees WHERE student_id=? AND currency=?", (st["id"], cur)).fetchone()[0]
            paid = c.execute("SELECT COALESCE(SUM(paid_cents),0) FROM fees WHERE student_id=? AND currency=?", (st["id"], cur)).fetchone()[0]
            fees[cur] = {"balance_cents": due - paid}
        grades = c.execute("SELECT * FROM grades WHERE student_id=?", (st["id"],)).fetchall()
        ann = c.execute("SELECT * FROM announcements WHERE audience IN ('all','students') ORDER BY id DESC").fetchall()
        c.close()
        return render_template("student.html", student=st, fees=fees, grades=grades, announcements=ann)
    if role == "parent":
        children = c.execute("SELECT * FROM students WHERE parent_id=?", (session["user_id"],)).fetchall()
        out = []
        for ch in children:
            ch = dict(ch)
            ch["fees"] = {}
            for cur in CURRENCIES:
                due = c.execute("SELECT COALESCE(SUM(amount_cents),0) FROM fees WHERE student_id=? AND currency=?", (ch["id"], cur)).fetchone()[0]
                paid = c.execute("SELECT COALESCE(SUM(paid_cents),0) FROM fees WHERE student_id=? AND currency=?", (ch["id"], cur)).fetchone()[0]
                ch["fees"][cur] = {"balance_cents": due - paid}
            ch["grades"] = c.execute("SELECT * FROM grades WHERE student_id=?", (ch["id"],)).fetchall()
            out.append(ch)
        ann = c.execute("SELECT * FROM announcements WHERE audience IN ('all','parents') ORDER BY id DESC").fetchall()
        c.close()
        return render_template("parent.html", parent={"full_name": session["full_name"]}, children=out, announcements=ann)
    if role == "bursar":
        totals = {}
        for cur in CURRENCIES:
            due = c.execute("SELECT COALESCE(SUM(amount_cents),0) FROM fees WHERE currency=?", (cur,)).fetchone()[0]
            paid = c.execute("SELECT COALESCE(SUM(paid_cents),0) FROM fees WHERE currency=?", (cur,)).fetchone()[0]
            totals[cur] = {"due_cents": due, "paid_cents": paid, "balance_cents": due - paid}
        students = c.execute("SELECT * FROM students ORDER BY full_name").fetchall()
        c.close()
        return render_template("bursar.html", totals=totals, students=students)
    c.close()
    return redirect(url_for("login"))

# --- ADMIN ACTIONS ---
@app.route("/admin/add-user", methods=["POST"])
@login_required
def admin_add_user():
    if session.get("role") != "admin":
        abort(403)
    f = request.form
    c = get_db()
    try:
        c.execute("INSERT INTO users(username,password_hash,full_name,role,phone) VALUES(?,?,?,?,?)", (f.get("username"), generate_password_hash(f.get("password")), f.get("full_name"), f.get("role"), f.get("phone", "")))
        c.commit()
        flash("User created!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    c.close()
    return redirect(url_for("dashboard"))

@app.route("/admin/announcement", methods=["POST"])
@login_required
def admin_post_announcement():
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    c.execute("INSERT INTO announcements(title,body,audience,created_at) VALUES(?,?,?,?)", (request.form.get("title"), request.form.get("body"), request.form.get("audience"), datetime.now(timezone.utc).isoformat()))
    c.commit(); c.close()
    flash("Announcement posted!", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/settings", methods=["POST"])
@login_required
def admin_settings():
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    for k in ["school_name", "motto", "location", "phone", "email"]:
        c.execute("INSERT INTO school_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, request.form.get(k, "")))
    c.commit(); c.close()
    flash("School settings saved! New name shows everywhere.", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/link-parent", methods=["POST"])
@login_required
def admin_link_parent():
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    c.execute("UPDATE students SET parent_id=? WHERE id=?", (request.form.get("parent_id"), request.form.get("student_id")))
    c.commit(); c.close()
    flash("Student linked to parent! Parent will now see this child.", "success")
    return redirect(url_for("dashboard"))

# --- TEACHER ACTIONS ---
@app.route("/teacher/grade", methods=["POST"])
@login_required
def teacher_add_grade():
    if session.get("role") not in ("teacher", "admin"):
        abort(403)
    c = get_db()
    c.execute("INSERT INTO grades(student_id,teacher_id,subject,term,academic_year,score) VALUES(?,?,?,?,?,?)", (request.form.get("student_id"), session["user_id"], request.form.get("subject"), request.form.get("term"), request.form.get("academic_year"), request.form.get("score")))
    c.commit(); c.close()
    flash("Grade saved!", "success")
    return redirect(url_for("dashboard"))

@app.route("/teacher/attendance", methods=["POST"])
@login_required
def teacher_mark_attendance():
    if session.get("role") not in ("teacher", "admin"):
        abort(403)
    c = get_db()
    c.execute("INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)", (request.form.get("student_id"), request.form.get("day"), request.form.get("status")))
    c.commit(); c.close()
    flash("Attendance saved!", "success")
    return redirect(url_for("dashboard"))

# --- BURSAR ACTIONS ---
@app.route("/bursar/payment", methods=["POST"])
@login_required
def bursar_add_payment():
    if session.get("role") not in ("bursar", "admin"):
        abort(403)
    amt = int(float(request.form.get("amount", 0)) * 100)
    c = get_db()
    c.execute("INSERT INTO payments(student_id,amount_cents,currency,method,created_at) VALUES(?,?,?,?,?)", (request.form.get("student_id"), amt, request.form.get("currency"), request.form.get("method"), datetime.now(timezone.utc).isoformat()))
    c.execute("UPDATE fees SET paid_cents = paid_cents + ? WHERE student_id=? AND currency=? AND paid_cents < amount_cents ORDER BY id LIMIT 1", (amt, request.form.get("student_id"), request.form.get("currency")))
    c.commit(); c.close()
    flash("Payment recorded!", "success")
    return redirect(url_for("dashboard"))

@app.route("/bursar/fee", methods=["POST"])
@login_required
def bursar_add_fee():
    if session.get("role") not in ("bursar", "admin"):
        abort(403)
    amt = int(float(request.form.get("amount", 0)) * 100)
    c = get_db()
    c.execute("INSERT INTO fees(student_id,category,amount_cents,currency,term,academic_year) VALUES(?,?,?,?,?,?)", (request.form.get("student_id"), request.form.get("category"), amt, request.form.get("currency"), request.form.get("term"), current_year()))
    c.commit(); c.close()
    flash("Fee assigned!", "success")
    return redirect(url_for("dashboard"))

# === V2: PUBLIC REGISTRATION ===
@app.route("/register", methods=["GET", "POST"])
def public_register():
    if request.method == "POST":
        f = request.form
        def save_file(field):
            fl = request.files.get(field)
            if fl and fl.filename:
                ext = os.path.splitext(fl.filename)[1].lower()
                if ext in ALLOWED_EXT:
                    fn = f"{field}_{secrets.token_hex(4)}{ext}"
                    fl.save(os.path.join(UPLOAD_FOLDER, fn))
                    return fn
            return ""
        c = get_db()
        c.execute("INSERT INTO applications(first_name,surname,dob,gender,school_level,grade_applying,prev_school,birth_cert_no,address,town,parent_name,parent_relation,parent_phone,parent_email,parent2_name,parent2_phone,nok_name,nok_phone,nok_relation,nok_address,birth_cert_file,results_file,parent_id_file,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',?)", (f.get("first_name"), f.get("surname"), f.get("dob"), f.get("gender"), f.get("school_level"), f.get("grade_applying"), f.get("prev_school"), f.get("birth_cert_no"), f.get("address"), f.get("town"), f.get("parent_name"), f.get("parent_relation"), f.get("parent_phone"), f.get("parent_email"), f.get("parent2_name"), f.get("parent2_phone"), f.get("nok_name"), f.get("nok_phone"), f.get("nok_relation"), f.get("nok_address"), save_file("birth_cert"), save_file("results"), save_file("parent_id"), datetime.now(timezone.utc).isoformat()))
        c.commit(); c.close()
        flash("Application received! School will contact you on WhatsApp / Email after review.", "success")
        return redirect(url_for("public_register"))
    return render_template("register.html")

@app.route("/admin/applications")
@login_required
def admin_applications():
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    apps = c.execute("SELECT * FROM applications ORDER BY id DESC").fetchall()
    c.close()
    return render_template("applications.html", apps=apps)

@app.route("/admin/applications/<int:aid>/approve", methods=["POST"])
@login_required
def approve_application(aid):
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    a = c.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
    if not a:
        flash("Not found", "error")
        return redirect(url_for("admin_applications"))
    s_code = gen_code("STU")
    p_code = gen_code("PAR")
    s_user = (a["first_name"] + "." + a["surname"]).lower().replace(" ", "")
    p_user = ("parent." + a["surname"]).lower().replace(" ", "")
    s_pass = gen_pass()
    p_pass = gen_pass()
    # Avoid duplicate usernames
    for suffix in ["", "1", "2"]:
        if not c.execute("SELECT 1 FROM users WHERE username=?", (s_user + suffix,)).fetchone():
            s_user = s_user + suffix
            break
    for suffix in ["", "1", "2"]:
        if not c.execute("SELECT 1 FROM users WHERE username=?", (p_user + suffix,)).fetchone():
            p_user = p_user + suffix
            break
    c.execute("INSERT INTO users(username,password_hash,full_name,role,phone,must_change_password) VALUES(?,?,?,?,?,1)", (s_user, generate_password_hash(s_pass), f"{a['first_name']} {a['surname']}", "student", a["parent_phone"]))
    s_uid = c.execute("SELECT id FROM users WHERE username=?", (s_user,)).fetchone()["id"]
    c.execute("INSERT INTO users(username,password_hash,full_name,role,phone,must_change_password) VALUES(?,?,?,?,?,1)", (p_user, generate_password_hash(p_pass), a["parent_name"], "parent", a["parent_phone"]))
    p_uid = c.execute("SELECT id FROM users WHERE username=?", (p_user,)).fetchone()["id"]
    full = f"{a['first_name']} {a['surname']}"
    c.execute("INSERT INTO students(user_id,parent_id,full_name,admission_no,class_name,phone,address,town,parent_phone,parent_email,nok_name,nok_phone,nok_relation,nok_address,school_level,grade_applying,prev_school,birth_cert_no,student_code) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (s_uid, p_uid, full, s_code, a["grade_applying"], a["parent_phone"], a["address"], a["town"], a["parent_phone"], a["parent_email"], a["nok_name"], a["nok_phone"], a["nok_relation"], a["nok_address"], a["school_level"], a["grade_applying"], a["prev_school"], a["birth_cert_no"], s_code))
    c.execute("UPDATE applications SET status='approved',student_code=?,parent_code=?,temp_student_user=?,temp_student_pass=?,temp_parent_user=?,temp_parent_pass=? WHERE id=?", (s_code, p_code, s_user, s_pass, p_user, p_pass, aid))
    c.commit(); c.close()
    flash(f"Approved! Student {s_code} / {s_user} / {s_pass} | Parent {p_code} / {p_user} / {p_pass} - Use WhatsApp button to send.", "success")
    return redirect(url_for("admin_applications"))

@app.route("/admin/applications/<int:aid>/reject", methods=["POST"])
@login_required
def reject_application(aid):
    if session.get("role") != "admin":
        abort(403)
    c = get_db()
    c.execute("UPDATE applications SET status='rejected' WHERE id=?", (aid,))
    c.commit(); c.close()
    flash("Rejected", "success")
    return redirect(url_for("admin_applications"))

@app.route("/teacher/assignments", methods=["GET", "POST"])
@login_required
def teacher_assignments():
    if session.get("role") not in ("teacher", "admin"):
        abort(403)
    if request.method == "POST":
        f = request.form
        fn = ""
        fl = request.files.get("file")
        if fl and fl.filename:
            fn = f"assign_{secrets.token_hex(4)}" + os.path.splitext(fl.filename)[1]
            fl.save(os.path.join(UPLOAD_FOLDER, fn))
        c = get_db()
        c.execute("INSERT INTO assignments(teacher_id,title,subject,class_name,due_date,details,file_name,created_at) VALUES(?,?,?,?,?,?,?,?)", (session["user_id"], f.get("title"), f.get("subject"), f.get("class_name"), f.get("due_date"), f.get("details"), fn, datetime.now(timezone.utc).isoformat()))
        c.commit(); c.close()
        flash("Assignment created! Now send via WhatsApp / Email below.", "success")
        return redirect(url_for("teacher_assignments"))
    c = get_db()
    assigns = c.execute("SELECT * FROM assignments ORDER BY id DESC").fetchall()
    studs = c.execute("SELECT s.* FROM students s").fetchall()
    # Fix parent_email: pull from students table
    c.close()
    return render_template("assignments.html", assigns=assigns, students=studs)

@app.route("/uploads/<fn>")
def uploaded_file(fn):
    return send_from_directory(UPLOAD_FOLDER, fn)

@app.route('/search')
def global_search():
    if session.get("role") not in ("teacher", "admin", "bursar", "parent"):
        return redirect("/login")
    q = request.args.get('q', '').strip()
    role = session.get("role", "")
    username = session.get("username", "")
    students, assigns, payments, users_list = [], [], [], []
    if q:
        c = get_db()
        like_q = f"%{q}%"
        try:
            students = c.execute("SELECT * FROM students WHERE name LIKE ? OR class LIKE ? OR parent_name LIKE ?", (like_q, like_q, like_q)).fetchall()
        except: students = []
        try:
            assigns = c.execute("SELECT * FROM assignments WHERE title LIKE ? OR subject LIKE ?", (like_q, like_q)).fetchall()
        except: assigns = []
        if role in ['admin', 'bursar']:
            try:
                payments = c.execute("SELECT * FROM payments WHERE student_name LIKE ?", (like_q,)).fetchall()
            except:
                try:
                    payments = c.execute("SELECT * FROM fees WHERE student_name LIKE ?", (like_q,)).fetchall()
                except: payments = []
        if role == 'admin':
            try:
                users_list = c.execute("SELECT * FROM users WHERE username LIKE ?", (like_q,)).fetchall()
            except: users_list = []
        c.close()
    html = f"""
    <h2>Search Results for "{q}"</h2>
    <form action="/search" method="GET"><input type="text" name="q" value="{q}" placeholder="Search..."> <button>Search</button></form>
    <a href="javascript:history.back()">Back</a>
    <h3>Students ({len(students)})</h3>
    """
    for s in students:
        html += f"<div><b>{s['name']}</b> - {s['class']} - {s['parent_name']}</div>"
    html += f"<h3>Assignments ({len(assigns)})</h3>"
    for a in assigns:
        html += f"<div><b>{a['title']}</b> - {a['subject']}</div>"
    if role in ['admin','bursar']:
        html += f"<h3>Payments ({len(payments)})</h3>"
        for p in payments:
            html += f"<div>{dict(p)}</div>"
    if role == 'admin':
        html += f"<h3>Users ({len(users_list)})</h3>"
        for u in users_list:
            html += f"<div><b>{u['username']}</b> - {u['role']}</div>"
    return html

# === PART 4: RUN ===
init_db()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
