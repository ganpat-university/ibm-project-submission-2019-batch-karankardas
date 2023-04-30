from flask import *
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import random
import re
import os
import smtplib
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import cv2
import glob
from vehicle_detector import VehicleDetector

global main_session
main_session = 0

# injects the environment variable in .env
load_dotenv()

app = Flask(__name__)
app.secret_key = "admin"

@app.after_request
def set_xss_protection_header(response):
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.after_request
def apply_caching(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

def get_user(email):
    db = sqlite3.connect('user_info.db')
    cursor = db.cursor()
    query = "SELECT * FROM users WHERE email = ?"
    params = (email,)
    cursor.execute(query, params)
    result = cursor.fetchone()
    if result:
        user = (result[0], result[1], result[2], result[3], result[4])
        return user
    else:
        return None

# Main Page
@app.route("/")
def home():
    return redirect(url_for('dashboard'))

# Login 
@app.route("/login", methods=['GET','POST'])
def login():
    if request.method == 'POST':
        db = sqlite3.connect('user_info.db')
        cursor = db.cursor()
        
        email = request.form['email']
        password = request.form['password']

        user = get_user(email)
        
        if user is None:
            return render_template('login.html', message="User doesn't Exist")

        elif user and check_password_hash(user[4],password):
            session['id'] = user[0]
            session['firstname'] = user[1]
            session['lastname'] = user[2]
            session['email'] = user[3]
            return redirect(url_for('send_otp'))
        else:
            return render_template('login.html', message="Invalid Email and password")
        
        # close the connection
        db.close()
    else:
        return render_template('login.html')

# register page
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        db = sqlite3.connect('user_info.db')
        cursor = db.cursor()

        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        passw = request.form['psw']
        
        user = get_user(email)

        pattern = r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+[\]{}|;:",./<>?`~])(?!.*\s).{8,}$'
        if user is None:
            if len(passw)>=8:
                if re.match(pattern,passw):
                    hashed_password = generate_password_hash(passw)
                    query = "INSERT INTO users (firstname, lastname, email, password) VALUES (?, ?, ?, ?)"
                    params = (firstname, lastname, email, hashed_password)
                    cursor.execute(query, params)
                    db.commit()
                else:
                    return render_template('createAreaManager.html',message='One Small,Upper,Special Required')
            else:
                return render_template('createAreaManager.html',message='Password Length >= 8')
        else:
            return render_template('createAreaManager.html',message='User Already Exist')
        
        return render_template('createAreaManager.html',message='User Account created Successfully')
    else:
        return render_template('createAreaManager.html')

# send otp after successfully login
@app.route("/send_otp", methods=['GET',"POST"])
def send_otp():
    otp = random.randint(100000, 999999)
    session["otp"] = otp
    email = session["email"]

    sender_email = os.getenv('EMAIL_ID')
    receiver_email = email
    password = os.getenv('PASSWORD')

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Signal Tech: Your OTP is "

    # Add message body
    body = f"Verification OTP number is : {otp}"
    message.attach(MIMEText(body, "plain"))

# Send the email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        return render_template('verify.html')

@app.route("/verify_otp", methods=['GET',"POST"])
def verify_otp():
    user_otp = request.form["otp"]
    if "otp" in session:
        otp = session["otp"]
        if otp == int(user_otp):
            global main_session
            main_session = 1
            return redirect(url_for('dashboard'))
        else:
            return render_template('verify.html', message='Invalid otp')
    else:
        return "Session expired. Please try again."

@app.route('/dashboard',methods=['GET','POST'])
def dashboard():
    if main_session == 1:
        return render_template('dashboard.html')
    else:
        return render_template('login.html', message="")
    
@app.route('/show_density', methods=['GET', 'POST'])
def show_density():
    # Load Veichle Detector
    vd = VehicleDetector()

    # Load images from a folder
    images_folder = glob.glob("images/*.jpg")

    vehicles_folder_count = 0

    lanes = []

    # Loop through all the images
    for img_path in images_folder:
        img = cv2.imread(img_path)

        vehicle_boxes = vd.detect_vehicles(img)
        vehicle_count = len(vehicle_boxes)

        # Update total count
        vehicles_folder_count += vehicle_count

        for box in vehicle_boxes:
            x, y, w, h = box

            cv2.rectangle(img, (x, y), (x + w, y + h), (25, 0, 180), 3)

            cv2.putText(img, "Vehicles: " + str(vehicle_count), (20, 50), 0, 2, (100, 200, 0), 3)

        lanes.append(vehicle_count)

        cv2.waitKey(0)

    cv2.destroyAllWindows()
    print(lanes)

    return render_template('showDensity.html', l1 = lanes[0], l2 = lanes[1], l3 = lanes[2], l4 = lanes[3])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
    
if __name__ == '__main__':
    app.run(debug=True)