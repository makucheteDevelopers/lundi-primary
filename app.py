import os
import secrets
import sqlite3
from datetime import date, datetime, timezone
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template,
                   request, session, url_for)
from jinja2 import DictLoader
from werkzeug.security import check_password_hash, generate_password_hash

# ==========================================================================
# 1. Configuration & Branding
# ==========================================================================
SCHOOL_NAME     = "Lundi Primary School"
SCHOOL_MOTTO    = "Knowledge · Integrity · Service"
SCHOOL_LOCATION = "Lundi, Midlands Province, Zimbabwe"

COMPANY_NAME    = "TransitLink Technologies"
COMPANY_TAGLINE = "Connecting Schools, Empowering Futures"
COMPANY_EMAIL   = "info@transitlink.co.zw"
COMPANY_WEBSITE = "www.transitlink.co.zw"

ROLES = ("admin", "teacher", "bursar", "parent", "student")
CURRENCIES = ("USD", "ZiG")
FEE_CATEGORIES = ("tuition", "sdc_levy", "exam_fee", "practical", "transport", "uniform", "stationery")
LEVELS = ("ECD A", "ECD B", "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7")
TERMS = ("Term 1", "Term 2", "Term 3")

def current_term():
    m = date.today().month
    return "Term 1" if m <= 4 else ("Term 2" if m <= 8 else "Term 3")

def current_year():
    return date.today().year

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lundi-primary-dev-secret-change-me")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lundi.db")

# ==========================================================================
# 2. HTML Templates (Stored in-memory for single-file deployment)
# ==========================================================================
# Note: The logo uses /static/transitlink_logo.png. If you haven't added the image yet,
# it will display the fallback text.
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}Portal{% endblock %} · {{ SCHOOL_NAME }}</title>
<style>
  :root{--navy:#0a1f44;--navy-deep:#061530;--navy-light:#1a3a6e;--gold:#d4af37;--gold-light:#e8c66a;--gold-dark:#b08d1c;--bg:#f4f1e8;--card:#fff;--ink:#1f2937;--muted:#6b7280;--ok:#047857;--bad:#b91c1c;}
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);display:flex;flex-direction:column;min-height:100vh;}
  header{background:linear-gradient(135deg,var(--navy-deep),var(--navy),var(--navy-light));border-bottom:3px solid var(--gold);color:#fff;padding:14px 22px;}
  header .top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
  header .name{font-weight:800;font-size:1.15rem;color:var(--gold-light)}
  header .motto{font-size:.78rem;opacity:.9;font-style:italic;color:#cbd5e1}
  header nav{display:flex;gap:14px;align-items:center;font-size:.88rem;flex-wrap:wrap}
  header a{color:var(--gold-light);text-decoration:none;opacity:.92}
  header a:hover{opacity:1;text-decoration:underline;color:var(--gold)}
  .badge{background:rgba(212,175,55,.15);border:1px solid rgba(212,175,55,.45);color:var(--gold-light);padding:3px 10px;border-radius:99px;font-size:.75rem;}
  main{flex:1;max-width:1200px;margin:22px auto;padding:0 16px 30px;width:100%}
  .card{background:var(--card);border-radius:12px;padding:18px 20px;box-shadow:0 1px 3px rgba(10,31,68,.08);border-top:3px solid var(--gold);margin-bottom:20px;}
  .card h2{margin:0 0 14px;font-size:1rem;color:var(--navy)}
  .grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
  .stat-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.6px;font-weight:600}
  .stat-value{font-size:1.55rem;font-weight:700;margin:.15rem 0;color:var(--navy)}
  table{width:100%;border-collapse:collapse;font-size:.88rem}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid #eef1f6}
  th{color:var(--navy);font-weight:700;font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;background:#faf8f2}
  input,select,button,textarea{font:inherit}
  input,select,textarea{padding:9px 10px;border:1px solid #d6dbe6;border-radius:8px;width:100%;background:#fff}
  input:focus,select:focus,textarea:focus{outline:2px solid var(--gold);border-color:var(--gold)}
  label.lbl{display:block;font-size:.75rem;color:var(--navy);font-weight:600;margin-bottom:4px}
  button{background:var(--navy);color:var(--gold-light);border:1px solid var(--gold);border-radius:8px;padding:10px 18px;cursor:pointer;font-weight:600;transition:all .15s;}
  button:hover{background:var(--navy-light);color:var(--gold)}
  button.gold{background:var(--gold);color:var(--navy);border-color:var(--gold-dark)}
  button.gold:hover{background:var(--gold-light)}
  form.inline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end}
  .flash{padding:11px 14px;border-radius:8px;margin-bottom:14px;font-size:.9rem;border-left:4px solid}
  .flash.error{background:#fee2e2;color:#991b1b;border-left-color:var(--bad)}
  .flash.success{background:#d1fae5;color:#065f46;border-left-color:var(--ok)}
  .muted{color:var(--muted);font-size:.85rem}
  .ok{color:var(--ok);font-weight:600} .bad{color:var(--bad);font-weight:600}
  .pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:600}
  .pill.ok{background:#d1fae5;color:#065f46} .pill.bad{background:#fee2e2;color:#991b1b} .pill.warn{background:#fef3c7;color:#92400e}
  .tag{display:inline-block;padding:2px 8px;border-radius:6px;background:#eef1f6;color:var(--navy);font-size:.72rem;margin-right:4px;font-weight:600}
  .login-wrap{max-width:440px;margin:6vh auto}
  .login-wrap h1{font-size:1.2rem;text-align:center;margin:0 0 4px;color:var(--navy)}
  .login-wrap .field{margin-bottom:12px}
  .branding-block{display:flex;flex-direction:column;align-items:center;text-align:center;background:#0a1f44;padding:20px;border-radius:12px;margin-top:24px;border:2px solid var(--gold);}
  .branding-block .brand-tag{font-size:.85rem;font-style:italic;color:#e8c66a;font-weight:600;margin-top:12px;}
  .branding-block .brand-contact{font-size:.78rem;color:#cbd5e1;margin-top:4px;}
  footer{background:linear-gradient(135deg,var(--navy-deep),var(--navy));border-top:3px solid var(--gold);color:#cbd5e1;padding:22px 16px;}
  .footer-inner{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;align-items:center;text-align:center;gap:12px;}
  .footer-text .tagline{font-size:.95rem;font-style:italic;color:#e8c66a;font-weight:600;}
  .footer-text .contact{font-size:.8rem;color:#94a3b8;margin-top:4px;}
  @media print{header,footer,button,.no-print,form{display:none!important}.card{box-shadow:none;border:1px solid #ccc;border-top:2px solid #d4af37;break-inside:avoid}body{background:#fff}}
</style>
</head>
<body>
<header>
  <div class="top">
    <div>
      <div class="name">🎓 {{ SCHOOL_NAME }}</div>
      <div class="motto">{{ SCHOOL_MOTTO }} · {{ SCHOOL_LOCATION }}</div>
    </div>
    <nav>
      {% if session.get('user_id') %}
        <span>{{ current_term }} {{ current_year }}</span>
        <span class="badge">{{ session.get('full_name') }} · {{ session.get('role')|capitalize }}</span>
        <a href="{{ url_for('logout') }}">Logout</a>
      {% endif %}
    </nav>
  </div>
</header>
<main>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
      <div class="flash {{ category }}">{{ message }}</div>
    {% endfor %}
  {% endwith %}
  {% block content %}{% endblock %}
</main>
<footer class="no-print">
  <div class="footer-inner">
    <img src="{{ url_for('static', filename='transitlink_logo.png') }}" 
         alt="TransitLink Technologies" 
         style="width: 90px; height: auto; border-radius: 10px; border: 1px solid rgba(212, 175, 55, 0.3);"
         onerror="this.style.display='none'; document.getElementById('fallback-logo').style.display='block';">
    <div id="fallback-logo" style="display:none; font-size:1.2rem; font-weight:bold; color:var(--gold);">TransitLink</div>
    <div class="footer-text">
      <div class="tagline">{{ COMPANY_TAGLINE }}</div>
      <div class="contact">{{ COMPANY_EMAIL }} &nbsp;|&nbsp; {{ COMPANY_WEBSITE }}</div>
    </div>
  </div>
</footer>
</body>
</html>
"""

LOGIN_HTML = """
{% extends 'base.html' %}{% block title %}Sign in{% endblock %}{% block content %}
<div class="login-wrap card">
  <h1>{{ SCHOOL_NAME }}</h1>
  <p class="muted" style="text-align:center;margin-bottom:20px;">Staff · Student · Parent Portal</p>
  <form method="post">
    <div class="field"><label>Username</label><input name="username" required autofocus></div>
    <div class="field"><label>Password</label><input type="password" name="password" required></div>
    <button type="submit" style="width:100%">Sign in</button>
  </form>
  <p class="muted" style="margin-top:16px;line-height:1.8">
    <strong>Demo accounts</strong><br>Admin: <code>admin / admin123</code> · Teacher: <code>teacher / teacher123</code><br>
    Bursar: <code>bursar / bursar123</code> · Parent: <code>parent1 / parent123</code> · Student: <code>student1 / student123</code>
  </p>
  <div class="branding-block">
    <img src="{{ url_for('static', filename='transitlink_logo.png') }}" 
         alt="TransitLink Logo" style="width: 140px; border-radius: 8px;" 
         onerror="this.style.display='none'; document.getElementById('login-fallback').style.display='block';">
    <div id="login-fallback" style="display:none; font-size:1.5rem; font-weight:bold; color:var(--gold); margin-bottom:10px;">TransitLink</div>
    <div class="brand-tag">{{ COMPANY_TAGLINE }}</div>
    <div class="brand-contact">{{ COMPANY_EMAIL }} · {{ COMPANY_WEBSITE }}</div>
  </div>
</div>
{% endblock %}
"""

ADMIN_HTML = """
{% extends 'base.html' %}{% block title %}Admin{% endblock %}{% block content %}
<div class="card"><h2>Head's Office — {{ SCHOOL_NAME }}</h2><p class="muted">{{ current_term }} · {{ current_year }}</p></div>
<div class="grid">
  <div class="card"><div class="stat-label">Students</div><div class="stat-value">{{ counts.students }}</div></div>
  <div class="card"><div class="stat-label">Teachers</div><div class="stat-value">{{ counts.teachers }}</div></div>
  <div class="card"><div class="stat-label">Parents</div><div class="stat-value">{{ counts.parents }}</div></div>
</div>
<div class="grid">
  {% for cur in CURRENCIES %}{% set t = totals[cur] %}
    <div class="card"><h2>Fee position — {{ cur }}</h2>
      <p class="muted">Billed {{ t.due_cents|money(cur) }} · Paid {{ t.paid_cents|money(cur) }}</p>
      <p class="stat-value {{ 'bad' if t.balance_cents > 0 else 'ok' }}">Outstanding: {{ t.balance_cents|money(cur) }}</p>
    </div>
  {% endfor %}
</div>
<div class="grid">
  <div class="card">
    <h2>Add a user</h2>
    <form method="post" action="{{ url_for('admin_add_user') }}" class="inline">
      <div><label class="lbl">Role</label><select name="role" required>
        <option value="student">Student</option><option value="teacher">Teacher</option>
        <option value="parent">Parent</option><option value="bursar">Bursar</option>
      </select></div>
      <div><label class="lbl">Username</label><input name="username" required></div>
      <div><label class="lbl">Full name</label><input name="full_name" required></div>
      <div><label class="lbl">Password</label><input name="password" type="password" required></div>
      <div><button type="submit">Create User</button></div>
    </form>
  </div>
  <div class="card">
    <h2>Post announcement</h2>
    <form method="post" action="{{ url_for('admin_post_announcement') }}">
      <label class="lbl">Title</label><input name="title" required>
      <label class="lbl" style="margin-top:8px">Body</label><textarea name="body" rows="3" required></textarea>
      <label class="lbl" style="margin-top:8px">Audience</label><select name="audience">
        <option value="all">Everyone</option><option value="staff">Staff</option>
        <option value="parents">Parents</option><option value="students">Students</option>
      </select>
      <button type="submit" style="margin-top:10px">Post</button>
    </form>
  </div>
</div>
<div class="card">
  <h2>All System Users</h2>
  <table><thead><tr><th>Username</th><th>Name</th><th>Role</th></tr></thead><tbody>
    {% for u in users %}<tr><td>{{ u.username }}</td><td>{{ u.full_name }}</td><td><span class="tag">{{ u.role }}</span></td></tr>{% endfor %}
  </tbody></table>
</div>
{% endblock %}
"""

TEACHER_HTML = """
{% extends 'base.html' %}{% block title %}Teacher{% endblock %}{% block content %}
<div class="card"><h2>Welcome, {{ teacher.full_name if teacher else session.full_name }}</h2><p class="muted">Subject: {{ teacher.subject if teacher else '—' }}</p></div>
<div class="grid">
  <div class="card">
    <h2>Record a grade</h2>
    <form method="post" action="{{ url_for('teacher_add_grade') }}" class="inline">
      <div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Subject</label><input name="subject" required></div>
      <div><label class="lbl">Term</label><select name="term">{% for t in TERMS %}<option>{{ t }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Score</label><input name="score" type="number" min="0" max="100" required></div>
      <input type="hidden" name="academic_year" value="{{ current_year }}">
      <div><button type="submit">Save</button></div>
    </form>
  </div>
  <div class="card">
    <h2>Mark attendance</h2>
    <form method="post" action="{{ url_for('teacher_mark_attendance') }}" class="inline">
      <div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Date</label><input name="day" type="date" value="{{ date.today() }}" required></div>
      <div><label class="lbl">Status</label><select name="status"><option value="present">Present</option><option value="absent">Absent</option><option value="late">Late</option></select></div>
      <div><button type="submit">Save</button></div>
    </form>
  </div>
</div>
{% endblock %}
"""

STUDENT_HTML = """
{% extends 'base.html' %}{% block title %}Student{% endblock %}{% block content %}
<div class="card">
  <h2>{{ student.full_name }}</h2>
  <p class="muted">Admission No: {{ student.admission_no }} · Class: {{ student.class_name }}</p>
</div>
<div class="grid">
  {% for cur, f in fees.items() %}
  <div class="card"><h2>Fee balance — {{ cur }}</h2>
    <p class="stat-value {{ 'bad' if f.balance_cents > 0 else 'ok' }}">{{ f.balance_cents|money(cur) }}</p>
  </div>{% endfor %}
</div>
<div class="card">
  <h2>Grades</h2>
  <table><thead><tr><th>Subject</th><th>Term</th><th>Score</th></tr></thead><tbody>
    {% for g in grades %}<tr><td>{{ g.subject }}</td><td>{{ g.term }}</td><td>{{ g.score }}</td></tr>{% else %}<tr><td colspan="3" class="muted">No grades yet.</td></tr>{% endfor %}
  </tbody></table>
</div>
{% endblock %}
"""

PARENT_HTML = """
{% extends 'base.html' %}{% block title %}Parent{% endblock %}{% block content %}
<div class="card"><h2>Parent / Guardian Portal</h2><p class="muted">{{ session.full_name }} — {{ children_data|length }} child(ren) enrolled.</p></div>
{% for c in children_data %}
<div class="card">
  <h2>{{ c.student.full_name }} ({{ c.student.class_name }})</h2>
  <div class="grid" style="margin-top:14px">
    {% for cur, f in c.fees.items() %}
    <div><h2>Fee balance — {{ cur }}</h2><p class="stat-value {{ 'bad' if f.balance_cents > 0 else 'ok' }}">{{ f.balance_cents|money(cur) }}</p></div>
    {% endfor %}
  </div>
  <h2 style="margin-top:18px">Recent Payments</h2>
  <table><thead><tr><th>Receipt</th><th>Amount</th><th>Date</th></tr></thead><tbody>
    {% for p in c.payments %}<tr><td>{{ p.receipt_no }}</td><td>{{ p.amount_cents|money(p.currency) }}</td><td>{{ p.created_at[:10] }}</td></tr>{% else %}<tr><td colspan="3" class="muted">No payments.</td></tr>{% endfor %}
  </tbody></table>
</div>
{% endfor %}
{% endblock %}
"""

BURSAR_HTML = """
{% extends 'base.html' %}{% block title %}Bursar{% endblock %}{% block content %}
<div class="card"><h2>Bursar / Finance Office</h2>
  <p><a href="{{ url_for('bursar_clearance') }}"><button class="gold">Fee clearance report (Grade 7)</button></a></p>
</div>
<div class="grid">
  <div class="card">
    <h2>Record a payment</h2>
    <form method="post" action="{{ url_for('bursar_add_payment') }}" class="inline">
      <div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Term</label><select name="term">{% for t in TERMS %}<option {% if t==current_term %}selected{% endif %}>{{ t }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Currency</label><select name="currency">{% for c in CURRENCIES %}<option>{{ c }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Amount</label><input name="amount" type="number" step="0.01" required></div>
      <input type="hidden" name="academic_year" value="{{ current_year }}">
      <div><button type="submit">Record</button></div>
    </form>
  </div>
  <div class="card">
    <h2>Set / update invoice</h2>
    <form method="post" action="{{ url_for('bursar_set_invoice') }}" class="inline">
      <div><label class="lbl">Student</label><select name="student_id">{% for s in students %}<option value="{{ s.id }}">{{ s.full_name }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Category</label><select name="category">{% for c in FEE_CATEGORIES %}<option>{{ c }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Currency</label><select name="currency">{% for c in CURRENCIES %}<option>{{ c }}</option>{% endfor %}</select></div>
      <div><label class="lbl">Amount Due</label><input name="amount_due" type="number" step="0.01" required></div>
      <div><label class="lbl">Term</label><select name="term">{% for t in TERMS %}<option {% if t==current_term %}selected{% endif %}>{{ t }}</option>{% endfor %}</select></div>
      <input type="hidden" name="academic_year" value="{{ current_year }}">
      <div><button type="submit">Save</button></div>
    </form>
  </div>
</div>
<div class="card">
  <h2>Recent Payments</h2>
  <table><thead><tr><th>Receipt</th><th>Student</th><th>Amount</th><th>Recorded By</th></tr></thead><tbody>
    {% for p in recent_payments %}<tr><td>{{ p.receipt_no }}</td><td>{{ p.full_name }}</td><td>{{ p.amount_cents|money(p.currency) }}</td><td>{{ p.recorded_by_name or 'Online (Gateway)' }}</td></tr>{% endfor %}
  </tbody></table>
</div>
{% endblock %}
"""

CLEARANCE_HTML = """
{% extends 'base.html' %}{% block title %}Clearance{% endblock %}{% block content %}
<div class="card">
  <h2>{{ SCHOOL_NAME }} — Fee clearance report</h2>
  <p class="muted">Grade 7 candidates (ZIMSEC primary exam) · {{ term }} {{ year }}</p>
  <button onclick="window.print()" class="no-print">Print Report</button>
</div>
<div class="card">
  <table><thead><tr><th>Student</th><th>Candidate No</th><th>USD Bal</th><th>ZiG Bal</th><th>Status</th></tr></thead><tbody>
    {% for r in report %}
    <tr>
      <td>{{ r.student.full_name }}</td><td>{{ r.student.candidate_no or '—' }}</td>
      {% for cur in CURRENCIES %}{% set f = r.fees[cur] %}<td class="{{ 'bad' if f.balance_cents > 0 else 'ok' }}">{{ f.balance_cents|money(cur) }}</td>{% endfor %}
      <td>{% if r.cleared %}<span class="pill ok">CLEARED</span>{% else %}<span class="pill bad">OUTSTANDING</span>{% endif %}</td>
    </tr>{% endfor %}
  </tbody></table>
</div>
{% endblock %}
"""

ERROR_HTML = """
{% extends 'base.html' %}{% block title %}Error{% endblock %}{% block content %}
<div class="card" style="text-align:center"><h2 style="font-size:2.4rem;">{{ code }}</h2><p class="muted">{{ message }}</p><p><a href="{{ url_for('dashboard') }}">← Back to dashboard</a></p></div>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base.html': BASE_HTML, 'login.html': LOGIN_HTML, 'admin.html': ADMIN_HTML,
    'teacher.html': TEACHER_HTML, 'student.html': STUDENT_HTML, 'parent.html': PARENT_HTML,
    'bursar.html': BURSAR_HTML, 'clearance.html': CLEARANCE_HTML, 'error.html': ERROR_HTML
})

# ==========================================================================
# 3. Database Setup & Helpers
# ==========================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE REFERENCES users(id), admission_no TEXT UNIQUE, class_name TEXT, candidate_no TEXT, parent_id INTEGER, enrolled_at TEXT);
CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE REFERENCES users(id), subject TEXT);
CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER REFERENCES students(id), term TEXT, academic_year INTEGER, category TEXT, currency TEXT, amount_cents INTEGER, created_at TEXT, UNIQUE(student_id, term, academic_year, category, currency));
CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER REFERENCES students(id), term TEXT, academic_year INTEGER, currency TEXT, amount_cents INTEGER, method TEXT, receipt_no TEXT UNIQUE, recorded_by INTEGER, gateway_ref TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS grades (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER REFERENCES students(id), subject TEXT, term TEXT, academic_year INTEGER, score REAL, teacher_id INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER REFERENCES students(id), day TEXT, status TEXT, UNIQUE(student_id, day));
CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, audience TEXT, posted_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def money(cents, currency="USD"):
    if cents is None: return "—"
    symbol = "US$" if currency == "USD" else "ZiG "
    sign = "-" if cents < 0 else ""
    return f"{sign}{symbol}{abs(cents) / 100:,.2f}"

app.jinja_env.filters['money'] = money

def fee_summary(db, student_id, currency="USD"):
    due = db.execute("SELECT COALESCE(SUM(amount_cents),0) s FROM invoices WHERE student_id=? AND currency=?", (student_id, currency)).fetchone()["s"]
    paid = db.execute("SELECT COALESCE(SUM(amount_cents),0) s FROM payments WHERE student_id=? AND currency=?", (student_id, currency)).fetchone()["s"]
    return {"currency": currency, "due_cents": due, "paid_cents": paid, "balance_cents": due - paid}

def all_fee_summaries(db, student_id):
    return {cur: fee_summary(db, student_id, cur) for cur in CURRENCIES}
def next_receipt_no(db, currency):
    year = date.today().year
    key = f"RCPT-{year}-{currency}"
    db.execute("INSERT INTO counters(name,value) VALUES(?,0) ON CONFLICT(name) DO NOTHING", (key,))
    db.execute("UPDATE counters SET value = value + 1 WHERE name=?", (key,))
    n = db.execute("SELECT value FROM counters WHERE name=?", (key,)).fetchone()["value"]
    return f"{key}-{n:05d}"

# ==========================================================================
# 4. Authentication & Route Decorators
# ==========================================================================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session: return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles: abort(403)
            return f(*args, **kwargs)
        return wrapper
    return deco

@app.context_processor
def inject_globals():
    return {"SCHOOL_NAME": SCHOOL_NAME, "SCHOOL_MOTTO": SCHOOL_MOTTO, "SCHOOL_LOCATION": SCHOOL_LOCATION,
            "current_term": current_term(), "current_year": current_year(), "CURRENCIES": CURRENCIES, "TERMS": TERMS}

# ==========================================================================
# 5. Routes
# ==========================================================================
@app.route("/")
def index(): return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.update(user_id=user["id"], role=user["role"], full_name=user["full_name"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/dashboard")
@login_required
def dashboard():
    db = get_db()
    try:
        role = session["role"]
        if role == "admin":
            counts = {"students": db.execute("SELECT COUNT(*) c FROM students").fetchone()["c"],
                      "teachers": db.execute("SELECT COUNT(*) c FROM teachers").fetchone()["c"],
                      "parents": db.execute("SELECT COUNT(*) c FROM users WHERE role='parent'").fetchone()["c"]}
            totals = {}
            for cur in CURRENCIES:
                due = db.execute("SELECT COALESCE(SUM(amount_cents),0) s FROM invoices WHERE currency=?", (cur,)).fetchone()["s"]
                paid = db.execute("SELECT COALESCE(SUM(amount_cents),0) s FROM payments WHERE currency=?", (cur,)).fetchone()["s"]
                totals[cur] = {"due_cents": due, "paid_cents": paid, "balance_cents": due - paid}
            return render_template("admin.html", counts=counts, totals=totals, users=db.execute("SELECT * FROM users").fetchall())

        elif role == "teacher":
            teacher = db.execute("SELECT t.*, u.full_name FROM teachers t JOIN users u ON u.id=t.user_id WHERE t.user_id=?", (session["user_id"],)).fetchone()
            students = db.execute("SELECT s.*, u.full_name FROM students s JOIN users u ON u.id=s.user_id").fetchall()
            return render_template("teacher.html", teacher=teacher, students=students, date=date)

        elif role == "student":
            student = db.execute("SELECT s.*, u.full_name FROM students s JOIN users u ON u.id=s.user_id WHERE s.user_id=?", (session["user_id"],)).fetchone()
            grades = db.execute("SELECT * FROM grades WHERE student_id=?", (student["id"],)).fetchall()
            return render_template("student.html", student=student, grades=grades, fees=all_fee_summaries(db, student["id"]))

        elif role == "parent":
            children = db.execute("SELECT s.*, u.full_name FROM students s JOIN users u ON u.id=s.user_id WHERE s.parent_id=?", (session["user_id"],)).fetchall()
            children_data = []
            for c in children:
                children_data.append({"student": c, "fees": all_fee_summaries(db, c["id"]),
                                      "payments": db.execute("SELECT * FROM payments WHERE student_id=? ORDER BY created_at DESC", (c["id"],)).fetchall()})
            return render_template("parent.html", children_data=children_data)

        elif role == "bursar":
            students = db.execute("SELECT s.*, u.full_name FROM students s JOIN users u ON u.id=s.user_id").fetchall()
            recent_payments = db.execute("""SELECT p.*, u.full_name, r.full_name AS recorded_by_name FROM payments p 
                                            JOIN students s ON s.id=p.student_id JOIN users u ON u.id=s.user_id 
                                            LEFT JOIN users r ON r.id=p.recorded_by ORDER BY p.created_at DESC LIMIT 15""").fetchall()
            return render_template("bursar.html", students=students, recent_payments=recent_payments)
    finally:
        db.close()
    abort(403)

# --- Admin Actions ---
@app.post("/admin/add-user")
@login_required
@role_required("admin")
def admin_add_user():
    db = get_db()
    try:
        uid = db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES (?,?,?,?,?)",
                         (request.form["username"].lower(), generate_password_hash(request.form["password"]),
                          request.form["full_name"], request.form["role"], now_iso())).lastrowid
        if request.form["role"] == "student":
            db.execute("INSERT INTO students (user_id, admission_no, class_name, enrolled_at) VALUES (?,?,?,?)",
                       (uid, f"ADM-{secrets.randbelow(9999):04d}", "Grade 1", now_iso()))
        elif request.form["role"] == "teacher":
            db.execute("INSERT INTO teachers (user_id, subject) VALUES (?,?)", (uid, "General"))
        db.commit()
        flash("User created successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Username already exists.", "error")
    finally:
        db.close()
    return redirect(url_for("dashboard"))

@app.post("/admin/announcement")
@login_required
@role_required("admin")
def admin_post_announcement():
    db = get_db()
    db.execute("INSERT INTO announcements (title, body, audience, posted_by, created_at) VALUES (?,?,?,?,?)",
               (request.form["title"], request.form["body"], request.form["audience"], session["user_id"], now_iso()))
    db.commit(); db.close()
    flash("Announcement posted.", "success")
    return redirect(url_for("dashboard"))

# --- Teacher Actions ---
@app.post("/teacher/grade")
@login_required
@role_required("teacher")
def teacher_add_grade():
    db = get_db()
    teacher = db.execute("SELECT id FROM teachers WHERE user_id=?", (session["user_id"],)).fetchone()
    db.execute("INSERT INTO grades (student_id, subject, term, academic_year, score, teacher_id, created_at) VALUES (?,?,?,?,?,?,?)",
               (request.form["student_id"], request.form["subject"], request.form["term"], request.form["academic_year"],
                float(request.form["score"]), teacher["id"] if teacher else None, now_iso()))
    db.commit(); db.close()
    flash("Grade recorded.", "success")
    return redirect(url_for("dashboard"))

@app.post("/teacher/attendance")
@login_required
@role_required("teacher")
def teacher_mark_attendance():
    db = get_db()
    db.execute("INSERT INTO attendance (student_id, day, status) VALUES (?,?,?) ON CONFLICT(student_id, day) DO UPDATE SET status=excluded.status",
               (request.form["student_id"], request.form["day"], request.form["status"]))
    db.commit(); db.close()
    flash("Attendance saved.", "success")
    return redirect(url_for("dashboard"))

# --- Bursar Actions ---
@app.post("/bursar/payment")
@login_required
@role_required("bursar")
def bursar_add_payment():
    db = get_db()
    currency = request.form["currency"]
    receipt = next_receipt_no(db, currency)
    amount_cents = int(round(float(request.form["amount"]) * 100))
    db.execute("INSERT INTO payments (student_id, term, academic_year, currency, amount_cents, method, receipt_no, recorded_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
               (request.form["student_id"], request.form["term"], request.form["academic_year"], currency,
                amount_cents, "Manual", receipt, session["user_id"], now_iso()))
    db.commit(); db.close()
    flash(f"Payment recorded. Receipt: {receipt}", "success")
    return redirect(url_for("dashboard"))

@app.post("/bursar/invoice")
@login_required
@role_required("bursar")
def bursar_set_invoice():
    db = get_db()
    amount_cents = int(round(float(request.form["amount_due"]) * 100))
    db.execute("""INSERT INTO invoices (student_id, term, academic_year, category, currency, amount_cents, created_at) 
                  VALUES (?,?,?,?,?,?,?) ON CONFLICT(student_id, term, academic_year, category, currency) DO UPDATE SET amount_cents=excluded.amount_cents""",
               (request.form["student_id"], request.form["term"], request.form["academic_year"], request.form["category"],
                request.form["currency"], amount_cents, now_iso()))
    db.commit(); db.close()
    flash("Invoice saved.", "success")
    return redirect(url_for("dashboard"))

@app.get("/bursar/clearance")
@login_required
@role_required("bursar", "admin")
def bursar_clearance():
    db = get_db()
    candidates = db.execute("SELECT s.*, u.full_name FROM students s JOIN users u ON u.id=s.user_id WHERE s.class_name='Grade 7'").fetchall()
    report = []
    for c in candidates:
        fees = all_fee_summaries(db, c["id"])
        report.append({"student": c, "fees": fees, "cleared": all(f["balance_cents"] <= 0 for f in fees.values())})
    db.close()
    return render_template("clearance.html", report=report)

@app.errorhandler(403)
def forbidden(e): return render_template("error.html", code=403, message="Permission denied."), 403

# ==========================================================================
# 6. Seed Data
# ==========================================================================
def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
        pwd = generate_password_hash("admin123")
        db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES ('admin', ?, 'Mrs. R. Moyo (Head)', 'admin', ?)", (pwd, now_iso()))
        
        pwd = generate_password_hash("teacher123")
        tid = db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES ('teacher', ?, 'Mr. T. Ncube', 'teacher', ?)", (pwd, now_iso())).lastrowid
        db.execute("INSERT INTO teachers (user_id, subject) VALUES (?, 'Mathematics')", (tid,))

        pwd = generate_password_hash("bursar123")
        bid = db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES ('bursar', ?, 'Mr. P. Dube', 'bursar', ?)", (pwd, now_iso())).lastrowid

        pwd = generate_password_hash("parent123")
        pid = db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES ('parent1', ?, 'Mrs. J. Moyo', 'parent', ?)", (pwd, now_iso())).lastrowid

        pwd = generate_password_hash("student123")
        sid = db.execute("INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES ('student1', ?, 'Brian Moyo', 'student', ?)", (pwd, now_iso())).lastrowid
        stid = db.execute("INSERT INTO students (user_id, admission_no, class_name, candidate_no, parent_id, enrolled_at) VALUES (?, 'ADM/2024/001', 'Grade 7', '17001', ?, ?)", (sid, pid, now_iso())).lastrowid

        # Invoices (USD & ZiG)
        db.execute("INSERT INTO invoices (student_id, term, academic_year, category, currency, amount_cents, created_at) VALUES (?, 'Term 1', ?, 'tuition', 'USD', 40000, ?)", (stid, current_year(), now_iso()))
        db.execute("INSERT INTO invoices (student_id, term, academic_year, category, currency, amount_cents, created_at) VALUES (?, 'Term 1', ?, 'tuition', 'ZiG', 200000, ?)", (stid, current_year(), now_iso()))
        
        # Payment
        receipt = next_receipt_no(db, "USD")
        db.execute("INSERT INTO payments (student_id, term, academic_year, currency, amount_cents, method, receipt_no, recorded_by, created_at) VALUES (?, 'Term 1', ?, 'USD', 20000, 'Cash', ?, ?, ?)", (stid, current_year(), receipt, bid, now_iso()))
        
        db.commit()
    db.close()

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)