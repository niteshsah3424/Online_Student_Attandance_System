import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import os
from werkzeug.utils import secure_filename
import face_recognition
import numpy as np
from datetime import datetime
from functools import wraps
import base64
import cv2

# ================= APP =================
app = Flask(__name__)
app.secret_key = "super_secret_key"

DATASET = "static/dataset"
os.makedirs(DATASET, exist_ok=True)

DB_NAME = "attendance.db"


# ================= DATABASE INIT =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll TEXT,
        name TEXT,
        image TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll TEXT,
        name TEXT,
        time TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users(username,password) VALUES (?,?)",
                      (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            error = "Username already exists ❌"
            conn.close()

    return render_template("signup.html", error=error)




# ================= LOGIN REQUIRED =================
def login_required(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return route_func(*args, **kwargs)
    return wrapper


# ================= FORGOT PASSWORD =================
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    message = None

    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("UPDATE users SET password=? WHERE username=?",
                  (new_password, username))
        conn.commit()
        conn.close()

        message = "Password updated successfully ✅"

    return render_template("forgot.html", message=message)



# ================= MARK ATTENDANCE =================
def mark_attendance(roll, name):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id FROM attendance WHERE roll=? AND date=?", (roll, today))

    if not c.fetchone():
        c.execute(
            "INSERT INTO attendance(roll,name,time,date) VALUES (?,?,?,?)",
            (roll, name, now, today)
        )
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


# ================= LOAD FACES =================
def load_known_faces():
    encodings = []
    names = []
    rolls = []

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT roll,name,image FROM students")
    rows = c.fetchall()
    conn.close()

    for roll, name, file in rows:
        path = os.path.join(DATASET, file)
        if not os.path.exists(path):
            continue

        try:
            img = face_recognition.load_image_file(path)
            enc = face_recognition.face_encodings(img)
            if enc:
                encodings.append(enc[0])
                names.append(name)
                rolls.append(roll)
        except:
            continue

    return encodings, names, rolls


# ================= FACE RECOGNITION =================
@app.route("/recognize", methods=["POST"])
@login_required
def recognize():
    data = request.json.get("image")

    if not data:
        return jsonify({"message": "No image received ❌"})

    image_data = data.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    known_encodings, known_names, known_rolls = load_known_faces()

    if not known_encodings:
        return jsonify({"message": "No registered faces found ❌"})

    encodings = face_recognition.face_encodings(rgb)

    if not encodings:
        return jsonify({"message": "No face detected ❌"})

    for enc in encodings:
        matches = face_recognition.compare_faces(known_encodings, enc)
        dist = face_recognition.face_distance(known_encodings, enc)

        if len(dist) > 0:
            best = np.argmin(dist)

            if matches[best] and dist[best] < 0.6:
                name = known_names[best]
                roll = known_rolls[best]

                if mark_attendance(roll, name):
                    return jsonify({"message": f"{name} Attendance Marked ✔"})
                else:
                    return jsonify({"message": f"{name} Already Marked Today ⚠"})

    return jsonify({"message": "Face Not Recognized ❌"})


# ================= VIEW ATTENDANCE =================
@app.route("/view-attendance")
@login_required
def view_attendance():
    date_filter = request.args.get("date")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if date_filter:
        c.execute("SELECT id,roll,name,time,date FROM attendance WHERE date=? ORDER BY date DESC", (date_filter,))
    else:
        c.execute("SELECT id,roll,name,time,date FROM attendance ORDER BY date DESC")

    records = c.fetchall()
    conn.close()

    return render_template("attendance_view.html", records=records)


# ================= DELETE RECORD =================
@app.route("/delete-attendance/<int:id>")
@login_required
def delete_attendance(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM attendance WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_attendance"))


# ================= CLEAR ALL =================
@app.route("/clear-attendance")
@login_required
def clear_attendance():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()
    return redirect(url_for("view_attendance"))


# ================= EXPORT CSV =================
@app.route("/export-attendance")
@login_required
def export_attendance():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT roll,name,time,date FROM attendance")
    rows = c.fetchall()
    conn.close()

    def generate():
        yield "Roll,Name,Time,Date\n"
        for row in rows:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance.csv"}
    )


# ================= REGISTER STUDENT =================
@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    msg = None
    if request.method == "POST":
        roll = request.form["roll"]
        name = request.form["name"]
        file = request.files["image"]

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(DATASET, filename))

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "INSERT INTO students(roll,name,image) VALUES (?,?,?)",
                (roll, name, filename)
            )
            conn.commit()
            conn.close()

            msg = "Student Registered ✔"

    return render_template("register.html", message=msg)


# ================= VIEW STUDENTS =================
@app.route("/students")
@login_required
def students():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT roll,name,image FROM students")
    data = c.fetchall()
    conn.close()
    return render_template("students.html", students=data)


# ================= CAMERA PAGES =================
@app.route("/configure-camera", methods=["GET", "POST"])
@login_required
def configure_camera():

    if request.method == "POST":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            return "❌ Camera Not Working"

        ret, frame = cap.read()
        cap.release()

        if ret:
            return "✅ Camera Working Properly"
        else:
            return "❌ Camera Opened but Frame Not Captured"

    return render_template("camera_config.html")


@app.route("/attendance")
@login_required
def attendance():
    return render_template("attendance.html")


# ================= AUTH =================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect(url_for("home"))
        else:
            error = "Invalid credentials ❌"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)