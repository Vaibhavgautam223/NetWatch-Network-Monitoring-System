import os
import ipaddress
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from monitor import ping_host
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-key")


# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------
def get_db():
    """Create a MySQL connection using environment variables."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "Vaibhav@123"),
        database=os.getenv("DB_NAME", "netwatch"),
        connection_timeout=5,
    )


def fetch_all(query, params=()):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def initialize_database():
    """Create the database tables. Create the database itself with schema.sql first."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                ip_address VARCHAR(45) NOT NULL UNIQUE,
                description VARCHAR(255) DEFAULT '',
                last_status VARCHAR(10) DEFAULT 'Unknown',
                last_response_ms DECIMAL(10,2) NULL,
                last_checked DATETIME NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                device_id INT NOT NULL,
                status VARCHAR(10) NOT NULL,
                response_ms DECIMAL(10,2) NULL,
                checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_logs_device FOREIGN KEY (device_id)
                    REFERENCES devices(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# Auth Decorator
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or len(password) < 6:
            flash("Username required and password must be at least 6 characters.", "error")
            return render_template("register.html")

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                flash("That username is already taken.", "error")
            else:
                app.logger.exception("Registration failed")
                flash("Could not create account.", "error")
            return render_template("register.html")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "conn" in locals() and conn.is_connected():
                conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            rows = fetch_all(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
        except Error:
            app.logger.exception("Login DB error")
            flash("Login failed: database error.", "error")
            return render_template("login.html")

        if rows and check_password_hash(rows[0]["password_hash"], password):
            session["user_id"] = rows[0]["id"]
            session["username"] = rows[0]["username"]
            flash(f"Welcome, {rows[0]['username']}!", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Main Dashboard
# ---------------------------------------------------------------------------
@app.route("/")
@login_required
def index():
    try:
        devices = fetch_all("SELECT * FROM devices ORDER BY name")
        total = len(devices)

        online = sum(1 for d in devices if d.get("last_status") == "Online")
        offline = sum(1 for d in devices if d.get("last_status") == "Offline")
        recent_logs = fetch_all("""
            SELECT l.status, l.response_ms, l.checked_at, d.name, d.ip_address
            FROM monitoring_logs l
            JOIN devices d ON d.id = l.device_id
            ORDER BY l.checked_at DESC LIMIT 10
        """)
        return render_template(
            "index.html", devices=devices, total=total, online=online,
            offline=offline, recent_logs=recent_logs
        )
    except Error:
        app.logger.exception("Database error")
        return render_template("error.html", message=(
            "Could not connect to MySQL. Check that MySQL is running, "
            "the database exists, and DB_* settings are correct."
        )), 500


# ---------------------------------------------------------------------------
# Device Routes (Add / Edit / Delete / Check)
# ---------------------------------------------------------------------------
@app.route("/devices/add", methods=["GET", "POST"])
@login_required
def add_device():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        ip_address = request.form.get("ip_address", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not ip_address:
            flash("Device name and IP address are required.", "error")
            return render_template("add_device.html")

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            flash("Enter a valid IPv4 or IPv6 address.", "error")
            return render_template("add_device.html")

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO devices (name, ip_address, description) VALUES (%s, %s, %s)",
                (name, ip_address, description)
            )
            conn.commit()
            flash("Device added successfully.", "success")
            return redirect(url_for("index"))
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                flash("That IP address is already registered.", "error")
            else:
                app.logger.exception("Could not add device")
                flash("Could not add device. Check the MySQL connection.", "error")
            return render_template("add_device.html")
        finally:
            if "cursor" in locals():
                cursor.close()
            if "conn" in locals() and conn.is_connected():
                conn.close()

    return render_template("add_device.html")


@app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
@login_required
def edit_device(device_id):
    # Fetch the existing device
    try:
        rows = fetch_all("SELECT * FROM devices WHERE id = %s", (device_id,))
        if not rows:
            flash("Device not found.", "error")
            return redirect(url_for("index"))
        device = rows[0]
    except Error:
        app.logger.exception("Database error")
        flash("Could not load device.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        ip_address = request.form.get("ip_address", "").strip()
        description = request.form.get("description", "").strip()

        if not name or not ip_address:
            flash("Device name and IP address are required.", "error")
            return render_template("edit_device.html", device=device)

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            flash("Enter a valid IPv4 or IPv6 address.", "error")
            return render_template("edit_device.html", device=device)

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE devices SET name = %s, ip_address = %s, description = %s WHERE id = %s",
                (name, ip_address, description, device_id)
            )
            conn.commit()
            flash("Device updated successfully.", "success")
            return redirect(url_for("index"))
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                flash("That IP address is already registered to another device.", "error")
            else:
                app.logger.exception("Could not update device")
                flash("Could not update device. Check the MySQL connection.", "error")
            return render_template("edit_device.html", device=device)
        finally:
            if "cursor" in locals():
                cursor.close()
            if "conn" in locals() and conn.is_connected():
                conn.close()

    return render_template("edit_device.html", device=device)


@app.post("/devices/<int:device_id>/delete")
@login_required
def delete_device(device_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM devices WHERE id = %s", (device_id,))
        conn.commit()
        flash("Device deleted.", "success" if cursor.rowcount else "error")
    except Error:
        app.logger.exception("Could not delete device")
        flash("Could not delete device.", "error")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()
    return redirect(url_for("index"))


@app.post("/devices/<int:device_id>/check")
@login_required
def check_device(device_id):
    try:
        rows = fetch_all("SELECT * FROM devices WHERE id = %s", (device_id,))
        if not rows:
            flash("Device not found.", "error")
            return redirect(url_for("index"))

        device = rows[0]
        status, response_ms = ping_host(device["ip_address"])
        checked_at = datetime.now()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE devices
            SET last_status = %s, last_response_ms = %s, last_checked = %s
            WHERE id = %s
        """, (status, response_ms, checked_at, device_id))
        cursor.execute("""
            INSERT INTO monitoring_logs (device_id, status, response_ms, checked_at)
            VALUES (%s, %s, %s, %s)
        """, (device_id, status, response_ms, checked_at))
        conn.commit()
        flash(f'{device["name"]}: {status}' +
              (f" ({response_ms} ms)" if response_ms is not None else ""), "success")
    except Error:
        app.logger.exception("Could not save monitoring result")
        flash("Network check ran, but the result could not be saved to MySQL.", "error")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals() and conn.is_connected():
            conn.close()
    return redirect(url_for("index"))


@app.post("/devices/check-all")
@login_required
def check_all_devices():
    try:
        devices = fetch_all("SELECT id, name, ip_address FROM devices ORDER BY id")
        for device in devices:
            status, response_ms = ping_host(device["ip_address"])
            checked_at = datetime.now()
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE devices SET last_status=%s, last_response_ms=%s, last_checked=%s
                    WHERE id=%s
                """, (status, response_ms, checked_at, device["id"]))
                cursor.execute("""
                    INSERT INTO monitoring_logs (device_id, status, response_ms, checked_at)
                    VALUES (%s, %s, %s, %s)
                """, (device["id"], status, response_ms, checked_at))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
        flash(f"Checked {len(devices)} device(s).", "success")
    except Error:
        app.logger.exception("Bulk monitoring failed")
        flash("Monitoring stopped because of a database error.", "error")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        initialize_database()
        print("NetWatch database tables are ready.")
    except Error as exc:
        print("MySQL setup failed. Create the database using schema.sql and check DB_* settings.")
        print(f"Details: {exc}")
        raise SystemExit(1)
    # Development server only. Do not expose this debug server to the public internet.
    app.run(debug=True)