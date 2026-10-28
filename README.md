# NetWatch — Network Monitoring System

A beginner-friendly BCA project built with Python, Flask, MySQL, HTML/CSS and TCP/IP ping checks.

## Features

- Add devices by IPv4 or IPv6 address
- Check one device or all registered devices
- Show the last reachability status and response time
- Save check history in MySQL
- Delete devices and their associated history

## Requirements

- Python 3.10 or newer
- MySQL Server (for example, MySQL 8)
- VS Code or another code editor
- A network connection and permission to check the IP devices

## Setup on Windows

1. Install and start MySQL Server.
2. Open MySQL Workbench or the MySQL command line.
3. Run the complete `schema.sql` file. It creates the `netwatch` database and its tables.
4. Open the project folder in VS Code.
5. Open Terminal in VS Code and create a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run:
   `.venv\Scripts\activate.bat`

6. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

7. Set the MySQL credentials in the same terminal. Change the password to the one configured on your machine:

   ```powershell
   $env:DB_HOST="localhost"
   $env:DB_PORT="3306"
   $env:DB_USER="root"
   $env:DB_PASSWORD="YOUR_MYSQL_PASSWORD"
   $env:DB_NAME="netwatch"
   $env:FLASK_SECRET_KEY="replace-with-a-long-random-value"
   ```

   If your MySQL root account has no password, set `DB_PASSWORD` to an empty string.

8. Start the application:

   ```powershell
   python app.py
   ```

9. Open `http://127.0.0.1:5000` in your browser.

## First test

- Add `127.0.0.1` with the name `This computer`.
- Click **Check**.
- A successful ping should show Online and may show a response time.
- You can also try your router's LAN IP, such as `192.168.1.1`, if that is the correct address for your network.

## Important notes

- A device can be working but still appear Offline if its firewall blocks ICMP ping. Ping measures ICMP reachability, not every service or application.
- A device must be reachable from the computer running NetWatch.
- The **Check all devices** action checks devices sequentially and can take a few seconds per device.
- This starter project uses manual checks, not continuous background polling.
- It is intended for local development and educational use. The built-in Flask debug server is not for production or public exposure.
- No login/authentication is included in this starter version. Keep it on your own trusted computer/network; do not expose it publicly.
- Do not monitor systems or networks without authorization.
- Database credentials are read from environment variables. Do not commit real passwords to source control.

## Database overview

### `devices`
Stores device name, IP address, description, last status, response time and check time.

### `monitoring_logs`
Stores each check result and timestamp. Deleting a device also deletes its logs.

## Troubleshooting

**`Access denied for user`** — check `DB_USER` and `DB_PASSWORD`.

**`Unknown database 'netwatch'`** — run `schema.sql` in MySQL.

**`Can't connect to MySQL server`** — start MySQL and check the port (usually 3306).

**Ping always shows Offline** — test the IP in Command Prompt with `ping 127.0.0.1`. Firewalls and network rules may block ping. Make sure the IP is correct.

**`ping` is not recognized** — verify that the operating system's ping utility is installed and available in PATH.
