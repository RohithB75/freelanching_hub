from flask import Blueprint, request, jsonify, session, redirect, render_template
from app import mysql  # make sure this matches your project structure
from flask import flash, redirect, url_for
from werkzeug.utils import secure_filename
import os   

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="chintu@7",
        database="freelancing_hub"
    )

# -------------------------------
# ✅ LOGIN ROUTE (FIXED)
# -------------------------------

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cur = conn.cursor()

        # =======================
        # 🔥 ADMIN LOGIN
        # =======================
        if role == 'admin':
            cur.execute("""
                SELECT id, email, password 
                FROM admin 
                WHERE email=%s AND password=%s
            """, (email, password))

            admin = cur.fetchone()

            if admin:
                session.clear()
                session['admin_id'] = admin[0]
                session['role'] = 'admin'

                conn.close()
                return redirect(url_for('main.addresources'))
            else:
                conn.close()
                return "Invalid Admin Login ❌"

        # =======================
        # 👤 USER LOGIN
        # =======================
        cur.execute("""
            SELECT id, name, email, phone, gender, password, role
            FROM users
            WHERE email=%s AND password=%s AND role=%s
        """, (email, password, role))

        user = cur.fetchone()

        if user:
            session.clear()

            session['user_id'] = user[0]
            session['role'] = user[6]

            conn.close()

            # ✅ REDIRECT BASED ON ROLE
            if role == 'employer':
                return redirect(url_for('main.profile'))

            elif role == 'employee':
                return redirect(url_for('main.employee_profile'))

        conn.close()
        return "Invalid Login ❌"

    return render_template('login.html')

# -------------------------------
# ✅ SIGNUP ROUTE
# -------------------------------
@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        name = request.form['name']
        gender = request.form['gender']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']

        image = request.files.get('image')
        filename = None

        if image and image.filename != '':
            filename = secure_filename(image.filename)

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            image.save(os.path.join(upload_folder, filename))

        # ✅ FIXED DB CODE
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (name, email, phone, password, role, image, gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, email, phone, password, role, filename, gender))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('signup.html')

# -------------------------------
# ✅ TEST ROUTE
# -------------------------------

import os
from werkzeug.utils import secure_filename
from flask import current_app, flash

@main.route('/post_project', methods=['GET', 'POST'])
def post_project():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        skills = request.form['skills']
        budget = request.form['budget']
        deadline = request.form['deadline']

        file = request.files.get('file')
        filename = None

        # ✅ FILE UPLOAD
        if file and file.filename != '':
            filename = secure_filename(file.filename)

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            file.save(os.path.join(upload_folder, filename))

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO projects (title, description, skills, budget, deadline, employer_id, file)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (title, description, skills, budget, deadline, session['user_id'], filename))

        conn.commit()
        conn.close()

        flash("Project posted successfully ✅", "success")

        return redirect(url_for('main.post_project'))

    return render_template('post_project.html')

@main.route('/projects')
def get_projects():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM projects 
        ORDER BY created_at DESC
    """)

    projects = cursor.fetchall()

    conn.close()

    return render_template('projects.html', projects=projects)
    
@main.route('/projects', methods=['GET'])
def get_projects_search():

    search = request.args.get('search')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("""
            SELECT * FROM projects
            WHERE title LIKE %s OR skills LIKE %s
            ORDER BY created_at DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("""
            SELECT * FROM projects 
            ORDER BY created_at DESC
        """)

    projects = cursor.fetchall()

    conn.close()

    return render_template('projects.html', projects=projects)

@main.route('/bid/<int:project_id>', methods=['POST'])
def bid_project(project_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    bid_amount = request.form['bid_amount']
    employee_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bids (project_id, employee_id, amount)
        VALUES (%s, %s, %s)
    """, (project_id, employee_id, bid_amount))

    conn.commit()
    conn.close()

    flash("Bid submitted successfully ✅", "success")

    return redirect(url_for('main.view_projects'))
    
@main.route('/lowest_bid/<int:project_id>')
def get_lowest_bid(project_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MIN(bid_amount) FROM bids WHERE project_id = %s
    """, (project_id,))

    lowest = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'lowest_bid.html',
        project_id=project_id,
        lowest_bid=lowest if lowest else 0
    )

@main.route('/bid/<int:project_id>', methods=['POST'])
def bid(project_id):

    # 🔐 Check login
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    # 📥 Get form data safely
    bid_amount = request.form.get('bid_amount')

    # ❌ Validation
    if not bid_amount:
        flash("Please enter a valid bid amount ❌", "error")
        return redirect(url_for('main.view_projects'))

    try:
        bid_amount = float(bid_amount)

        if bid_amount <= 0:
            flash("Bid must be greater than 0 ❌", "error")
            return redirect(url_for('main.view_projects'))

    except ValueError:
        flash("Invalid number format ❌", "error")
        return redirect(url_for('main.view_projects'))

    # 💾 DB insert
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO bids (project_id, employee_id, amount)
        VALUES (%s, %s, %s)
    """, (project_id, session['user_id'], bid_amount))

    conn.commit()
    conn.close()

    # ✅ Success message
    flash("Bid submitted successfully ✅", "success")

    return redirect(url_for('main.view_projects'))

@main.route('/assign_task/<int:project_id>/<int:employee_id>/<int:amount>')
def assign_task(project_id, employee_id, amount):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Insert ONLY existing columns
    cursor.execute("""
        INSERT INTO assigned_tasks 
        (project_id, employee_id, bid_amount, status, progress, employer_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        project_id,
        employee_id,
        amount,
        'Assigned',
        0,
        session['user_id']   # ✅ VERY IMPORTANT
    ))

    # ✅ VERY IMPORTANT → mark project as assigned
    cursor.execute("""
        UPDATE projects 
        SET status = 'assigned'
        WHERE id = %s
    """, (project_id,))


    conn.commit()
    conn.close()

    return redirect(url_for('main.assigned_tasks'))

@main.route('/assigned_tasks')
def assigned_tasks():

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            a.id,
            a.project_id,
            a.employee_id,
            a.bid_amount,
            a.status,
            a.progress,
            a.created_at AS assigned_date,

            p.title,
            p.description,
            p.deadline,
            p.created_at AS posted_on,
            p.file,

            u.name,
            u.email,
            u.phone

        FROM assigned_tasks a
        JOIN projects p ON a.project_id = p.id
        JOIN users u ON a.employee_id = u.id

        WHERE p.employer_id = %s
    """, (session['user_id'],))

    tasks = cur.fetchall()
    conn.close()

    return render_template('assigned_tasks.html', tasks=tasks)

@main.route('/update_progress/<int:task_id>', methods=['POST'])
def update_progress(task_id):

    if 'user_id' not in session:
        return {"status": "error", "message": "Not logged in"}

    # 📥 Get JSON data
    data = request.get_json()
    progress = data.get('progress')

    # ✅ Validate input
    try:
        progress = int(progress)
        if progress < 0:
            return {"status": "error", "message": "Progress cannot be negative"}
    except:
        return {"status": "error", "message": "Invalid input"}

    conn = get_db_connection()
    cur = conn.cursor()

    # 🔥 STEP 1: Get current progress
    cur.execute("SELECT progress FROM assigned_tasks WHERE id = %s", (task_id,))
    result = cur.fetchone()

    current_progress = result[0] if result and result[0] is not None else 0

    # 🔥 STEP 2: Add new progress
    updated_progress = current_progress + progress

    # 🔥 STEP 3: Limit to 100%
    if updated_progress > 100:
        updated_progress = 100

    # 🔥 STEP 4: Update DB
    cur.execute("""
        UPDATE assigned_tasks 
        SET progress = %s 
        WHERE id = %s
    """, (updated_progress, task_id))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "new_progress": updated_progress
    }

@main.route('/task_status/<int:task_id>')
def task_status(task_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    #post update progress
    if request.method =='POST':
        new_progress ==request.form.get("progress")

        cursor.execute("""
                       UPDATE assigned_tasks
                       SET progress = %s
                       WHERE id = %s
                       """,(new_progress, task_id))
        conn.commit()
    # GET fetch progress
    cursor.execute("""
        SELECT progress FROM assigned_tasks WHERE id = %s
    """, (task_id,))

    task = cursor.fetchone()

    conn.close()

    progress = task['progress'] if task and task['progress'] else 0

    return render_template(
        'task_status.html',
        task_id=task_id,
        progress=progress
    )
    

@main.route('/make_payment/<int:task_id>', methods=['POST'])
def make_payment(task_id):

    if 'user_id' not in session:
        return jsonify({"success": False})

    data = request.get_json()
    amount = data.get('amount')

    if not amount or float(amount) <= 0:
        return jsonify({"success": False})

    conn = get_db_connection()
    cur = conn.cursor()

    # ✅ INSERT PAYMENT
    cur.execute("""
        INSERT INTO payments (task_id, amount)
        VALUES (%s, %s)
    """, (task_id, amount))

    conn.commit()
    conn.close()

    return jsonify({"success": True})
    
@main.route('/payment_summary/<int:task_id>')
def payment_summary(task_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total paid
    cursor.execute("""
        SELECT SUM(amount) AS total_paid 
        FROM payments 
        WHERE task_id = %s
    """, (task_id,))
    payment_data = cursor.fetchone()

    # Total bid amount
    cursor.execute("""
        SELECT bid_amount 
        FROM assigned_tasks 
        WHERE id = %s
    """, (task_id,))
    task_data = cursor.fetchone()

    conn.close()

    total_paid = payment_data['total_paid'] if payment_data['total_paid'] else 0
    total_bid = task_data['bid_amount'] if task_data else 0

    return render_template(
        'payment_summary.html',
        task_id=task_id,
        total_paid=total_paid,
        total_bid=total_bid
    )
    
@main.route('/employer')
def employer():
    return render_template('employer_dashboard.html')

@main.route('/employee')
def employee():
    return render_template('employee_dashboard.html')

@main.route('/view_projects')
def view_projects():

    if 'user_id' not in session or session['role'] != 'employee':
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM projects WHERE status='open'")
    projects = cur.fetchall()

    conn.close()

    return render_template('view_projects.html', projects=projects)

@main.route('/my_tasks')
def my_tasks():

    if 'user_id' not in session or session['role'] != 'employee':
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
    SELECT 
        a.id,
        a.project_id,
        a.bid_amount,
        a.status,
        a.progress,
        a.created_at AS assigned_date,

        p.title,
        p.description,
        p.deadline,
        p.created_at AS posted_on,
        p.file,

        u.name AS employer_name,
        u.email,
        u.phone

    FROM assigned_tasks a
    JOIN projects p ON a.project_id = p.id
    JOIN users u ON p.employer_id = u.id

    WHERE a.employee_id = %s
""", (session['user_id'],))

    tasks = cur.fetchall()

    conn.close()

    return render_template('my_tasks.html', tasks=tasks)

@main.route('/view_my_projects')
def view_my_projects():

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Get only logged-in employer's projects
    cur.execute("""
        SELECT * FROM projects 
        WHERE employer_id = %s AND status= 'open' 
    """, (session['user_id'],))

    projects = cur.fetchall()

    conn.close()

    return render_template('view_my_projects.html', projects=projects)

@main.route('/view_bids/<int:project_id>')
def view_bids(project_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT b.*, u.name, u.email 
        FROM bids b
        JOIN users u ON b.employee_id = u.id
        WHERE b.project_id = %s
    """, (project_id,))

    bids = cur.fetchall()

    conn.close()

    # ✅ FIXED: use 'amount' instead of 'bid_amount'
    lowest_bid = min(bids, key=lambda x: x['amount'])['amount'] if bids else None

    return render_template('view_bids.html', bids=bids, lowest_bid=lowest_bid)

@main.route('/payment/<int:task_id>', methods=['GET', 'POST'])
def payment(task_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        amount = request.form['amount']

        cur.execute("""
            UPDATE assigned_tasks 
            SET paid = paid + %s 
            WHERE id = %s
        """, (amount, task_id))

        conn.commit()
        conn.close()

        return redirect(url_for('main.view_assigned_tasks'))

    # ✅ GET → show payment page
    cur.execute("SELECT * FROM assigned_tasks WHERE id = %s", (task_id,))
    task = cur.fetchone()

    conn.close()

    return render_template('payment.html', task=task)

@main.route('/get_payment/<int:task_id>')
def get_payment(task_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM payments
        WHERE task_id = %s
    """, (task_id,))

    total = cur.fetchone()[0]

    conn.close()

    return {"total_paid": float(total)}

@main.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM admin 
            WHERE email=%s AND password=%s
        """, (email, password))

        admin = cur.fetchone()

        conn.close()

        if admin:
            session.clear()
            session['admin_id'] = admin[0]
            session['role'] = 'admin'

            return redirect(url_for('main.addresources'))
        else:
            return "Invalid admin login ❌"

    return render_template('admin_login.html')

@main.route('/addresources', methods=['GET', 'POST'])
def addresources():

    if 'admin_id' not in session:
        return redirect(url_for('main.admin_login'))

    if request.method == 'POST':
        title = request.form['title']
        skills = request.form['skills']
        file = request.files['file']

        if file:
            filename = secure_filename(file.filename)

            # 🔥 FILE PATH
            BASE_DIR = os.path.abspath(os.path.dirname(__file__))
            upload_path = os.path.join(BASE_DIR, '..', 'static', 'uploads')
            upload_path = os.path.abspath(upload_path)

            os.makedirs(upload_path, exist_ok=True)

            file.save(os.path.join(upload_path, filename))

            # ✅ FIXED DB CODE
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO resources (title, skills, file)
                VALUES (%s, %s, %s)
            """, (title, skills, filename))

            conn.commit()
            conn.close()

        return redirect(url_for('main.addresources'))

    return render_template('addresources.html')

@main.route('/viewresources', methods=['GET'])
def viewresources():

    # ✅ Allow both admin & employee
    if 'user_id' not in session and 'admin_id' not in session:
        return redirect(url_for('main.login'))

    search = request.args.get('search')

    # Choose the navbar/layout based on who is viewing the page.
    if 'admin_id' in session:
        role = 'admin'
        layout = 'admin_base.html'
    else:
        role = 'employee'
        layout = 'employee_base.html'

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if search:
        cur.execute("""
            SELECT * FROM resources 
            WHERE skills LIKE %s
        """, ('%' + search + '%',))
    else:
        cur.execute("SELECT * FROM resources")

    resources = cur.fetchall()
    conn.close()

    return render_template('viewresources.html', resources=resources, role=role, layout=layout)

@main.route('/delete_resource/<int:id>')
def delete_resource(id):

    if 'admin_id' not in session:
        return redirect(url_for('main.admin_login'))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM resources WHERE id=%s", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for('main.viewresources'))

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.home'))



from flask import session, redirect, url_for, request, render_template, flash
from werkzeug.security import generate_password_hash

# ================= PROFILE =================
@main.route('/profile')
def profile():

    if 'role' not in session or session['role'] != 'employer':
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    conn.close()

    return render_template('profile.html', user=user)


# ================= MANAGE PROFILE =================
@main.route('/manage_profile', methods=['GET', 'POST'])
def manage_profile():

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        image = request.files.get('image')

        filename = None

        # 🔥 IMAGE UPDATE
        if image and image.filename != '':
            from werkzeug.utils import secure_filename
            from flask import current_app
            import os

            filename = secure_filename(image.filename)

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            image.save(os.path.join(upload_folder, filename))

        # 🔥 UPDATE QUERY
        if password and filename:
            cur.execute("""
                UPDATE users SET phone=%s, password=%s, image=%s WHERE id=%s
            """, (phone, password, filename, user_id))

        elif password:
            cur.execute("""
                UPDATE users SET phone=%s, password=%s WHERE id=%s
            """, (phone, password, user_id))

        elif filename:
            cur.execute("""
                UPDATE users SET phone=%s, image=%s WHERE id=%s
            """, (phone, filename, user_id))

        else:
            cur.execute("""
                UPDATE users SET phone=%s WHERE id=%s
            """, (phone, user_id))

        conn.commit()
        conn.close()

        return redirect(url_for('main.profile'))

    # GET
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    conn.close()

    return render_template('manage_profile.html', user=user)

@main.route('/delete_project/<int:project_id>')
def delete_project(project_id):

    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # 🔐 ensure user deletes only their project
    cur.execute("""
        DELETE FROM projects 
        WHERE id=%s AND employer_id=%s
    """, (project_id, session['user_id']))

    conn.commit()
    conn.close()

    flash("Project deleted successfully 🗑️", "success")

    return redirect(url_for('main.view_my_projects'))

@main.route('/admin_logout')
def admin_logout():
    session.clear()   # ✅ clears everything (safe & clean)
    return redirect(url_for('main.home'))  # or login page

@main.route('/employee_profile')
def employee_profile():

    if 'user_id' not in session or session['role'] != 'employee':
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    conn.close()

    return render_template('employee_profile.html', user=user)