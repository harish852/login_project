from flask import Flask, render_template, request, redirect, session
import pymysql
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import webbrowser
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# ✅ Helper to connect to MySQL using environment variables
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST"),
        port=int(os.getenv("MYSQLPORT", 3306)),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE")
    )


@app.route('/')
def home():
    return render_template('login.html')


def send_email_otp(recipient_email, otp):
    sender_email = "harishjeeva71@gmail.com"
    sender_password = "cxbn omnm actf jwzl"

    subject = "Your OTP Verification Code"
    body = f"Your OTP is: {otp}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Email sending failed:", e)
        return False


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        image = request.files['image']

        if image:
            image_filename = f"{name}_{image.filename}"
            image.save(os.path.join('static/uploads', image_filename))
            session['image_path'] = f"uploads/{image_filename}"

        try:
            db = get_db_connection()
            cur = db.cursor()
            cur.execute("SELECT * FROM emp_details WHERE name = %s", (name,))
            existing_user = cur.fetchone()
            cur.close()
            db.close()

            if existing_user:
                return render_template('signup.html', message="Username already exists. Please choose another.", success=False)
        except Exception as e:
            return f"Database error while checking username: {e}"

        otp = random.randint(1000, 9999)
        session['otp'] = otp
        session['name'] = name
        session['email'] = email
        session['password'] = password

        success = send_email_otp(email, otp)
        if success:
            return redirect('/otp')
        else:
            return "Failed to send OTP via email."

    return render_template('signup.html', error="Username already exists.")


@app.route('/otp', methods=['GET', 'POST'])
def otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp', type=int)
        if user_otp == session.get('otp'):
            try:
                db = get_db_connection()
                cur = db.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS emp_details (
                        name VARCHAR(50) not null unique,
                        email VARCHAR(100) not null,
                        password VARCHAR(255),
                        image_path VARCHAR(255)
                    )
                """)
                cur.execute("INSERT INTO emp_details (name, email, password, image_path) VALUES (%s, %s, %s, %s)",
                            (session['name'], session['email'], session['password'], session.get('image_path')))
                db.commit()
                cur.close()
                db.close()
                session.clear()
                return render_template('login.html', message="Sign up successful!! You can now login", success=True)
            except Exception as e:
                return f"Database error: {e}"
        else:
            return render_template('otp.html', message="Invalid OTP.", success=False)

    return render_template('otp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        try:
            db = get_db_connection()
            cur = db.cursor()
            cur.execute("SELECT name, email, password, image_path FROM emp_details WHERE name = %s", (name,))
            result = cur.fetchone()
            cur.close()
            db.close()

            if result:
                db_name, db_email, db_password, image_path = result
                if password == db_password:
                    session['user'] = {'name': db_name, 'email': db_email, 'image_path': image_path}
                    return render_template('dashboard.html', user=session['user'])
                else:
                    return render_template('login.html', message="Incorrect password.", success=False)
            else:
                return render_template('login.html', message="Username not found.", success=False)

        except Exception as e:
            return f"Database error: {e}"

    return render_template('login.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        new_password = request.form['new_password']

        try:
            db = get_db_connection()
            cur = db.cursor()
            cur.execute("SELECT * FROM emp_details WHERE name = %s AND email = %s", (name, email))
            result = cur.fetchone()

            if result:
                cur.execute("UPDATE emp_details SET password = %s WHERE name = %s AND email = %s",
                            (new_password, name, email))
                db.commit()
                message = 'Password reset successfully.'
            else:
                message = 'Invalid username or email.'

            cur.close()
            db.close()
        except Exception as e:
            message = f"Database error: {e}"

    return render_template('reset_password.html', message=message)


@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return redirect('/')


@app.route('/profile')
def profile():
    if 'user' in session:
        return render_template('profile.html', user=session['user'])
    return redirect('/')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/')


# This part is not used on the deployed web server, so can be removed or left for local testing
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    print("🚀 Starting Flask server...")
    app.run(debug=True, use_reloader=False)
