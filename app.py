from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")


def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        phone TEXT,
        address TEXT,
        hospital TEXT,
        specialization TEXT,
        health_problem TEXT,
        assigned_doctor TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        doctor TEXT,
        date TEXT,
        time TEXT,
        status TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        doctor TEXT,
        file TEXT,
        description TEXT
    )''')

    con.commit()
    con.close()


init_db()

# ---------------- HOME ----------------
@app.route('/')
def index():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        con = get_db()
        cur = con.cursor()

        cur.execute('''INSERT INTO users
        (name,email,password,role,phone,address,hospital,specialization,health_problem,assigned_doctor)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (data['name'], data['email'], data['password'], data['role'],
         data['phone'], data['address'],
         data.get('hospital'), data.get('specialization'),
         data.get('health_problem'), data.get('assigned_doctor')))

        con.commit()
        return redirect('/login')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        con = get_db()
        cur = con.cursor()

        user = cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()

        if user:
            session['user'] = user[1]
            session['role'] = user[4]

            if user[4] == "admin":
                return redirect('/admin')
            elif user[4] == "doctor":
                return redirect('/doctor')
            else:
                return redirect('/patient')

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- ADMIN ----------------
@app.route('/admin')
def admin():
    con = get_db()
    cur = con.cursor()

    patients = cur.execute("SELECT * FROM users WHERE role='patient'").fetchall()
    doctors = cur.execute("SELECT * FROM users WHERE role='doctor'").fetchall()

    return render_template("dashboard_admin.html", patients=patients, doctors=doctors)

# ---------------- DOCTOR ----------------
@app.route('/doctor')
def doctor():
    con = get_db()
    cur = con.cursor()

    patients = cur.execute("SELECT * FROM users WHERE assigned_doctor=?", (session['user'],)).fetchall()
    appointments = cur.execute("SELECT * FROM appointments WHERE doctor=?", (session['user'],)).fetchall()

    return render_template("dashboard_doctor.html", patients=patients, appointments=appointments)

# ---------------- APPROVE APPOINTMENT ----------------
@app.route('/approve/<id>')
def approve(id):
    con = get_db()
    cur = con.cursor()

    cur.execute("UPDATE appointments SET status='Approved' WHERE id=?", (id,))
    con.commit()
    return redirect('/doctor')

@app.route('/reject/<id>')
def reject(id):
    con = get_db()
    cur = con.cursor()

    cur.execute("UPDATE appointments SET status='Rejected' WHERE id=?", (id,))
    con.commit()
    return redirect('/doctor')

# ---------------- PATIENT ----------------
@app.route('/patient')
def patient():
    con = get_db()
    cur = con.cursor()

    doctors = cur.execute("SELECT name FROM users WHERE role='doctor'").fetchall()

    reports = cur.execute("SELECT * FROM reports WHERE patient=?", (session['user'],)).fetchall()

    # NEW 🔥
    appointments = cur.execute("SELECT * FROM appointments WHERE patient=?", (session['user'],)).fetchall()

    return render_template("dashboard_patient.html",
                           doctors=doctors,
                           reports=reports,
                           appointments=appointments)

# ---------------- BOOK APPOINTMENT ----------------
@app.route('/book', methods=['POST'])
def book():
    data = request.form
    con = get_db()
    cur = con.cursor()

    cur.execute("INSERT INTO appointments (patient,doctor,date,time,status) VALUES (?,?,?,?,?)",
                (session['user'], data['doctor'], data['date'], data['time'], "Pending"))

    con.commit()
    return redirect('/patient')

# ---------------- UPLOAD REPORT ----------------
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    desc = request.form['desc']

    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        con = get_db()
        cur = con.cursor()

        cur.execute("INSERT INTO reports (patient,doctor,file,description) VALUES (?,?,?,?)",
                    (session['user'], "", filename, desc))

        con.commit()

    return redirect('/patient')

# ---------------------- PROFILE ROUTE --------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    con = get_db()
    cur = con.cursor()

    user = cur.execute("SELECT * FROM users WHERE name=?", (session['user'],)).fetchone()

    if request.method == 'POST':
        data = request.form

        cur.execute('''UPDATE users SET 
            name=?, phone=?, address=?, hospital=?, specialization=?, health_problem=?, assigned_doctor=?
            WHERE email=?''',
        (data['name'], data['phone'], data['address'],
         data.get('hospital'), data.get('specialization'),
         data.get('health_problem'), data.get('assigned_doctor'),
         user[2]))

        con.commit()
        return redirect('/profile')

    return render_template("profile.html", user=user)

# ---------------------- APPOINTMENT VIEW ROUTE-----------------
@app.route('/appointments')
def appointments():
    con = get_db()
    cur = con.cursor()

    if session['role'] == "doctor":
        data = cur.execute("SELECT * FROM appointments WHERE doctor=?", (session['user'],)).fetchall()
    else:
        data = cur.execute("SELECT * FROM appointments WHERE patient=?", (session['user'],)).fetchall()

    return render_template("appointment.html", appointments=data)

# ---------------------- DELETE REPORT ------------------------
@app.route('/delete_report/<id>')
def delete_report(id):
    con = get_db()
    cur = con.cursor()

    cur.execute("DELETE FROM reports WHERE id=?", (id,))
    con.commit()

    return redirect('/patient')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)