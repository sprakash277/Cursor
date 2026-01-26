# Application Startup Guide

This guide provides detailed instructions for starting the Contest Scoring System application.

## Table of Contents

1. [Quick Comparison](#quick-comparison)
2. [Method 1: Manual Start (start.sh)](#method-1-manual-start-startsh)
3. [Method 2: Systemd Service](#method-2-systemd-service)
4. [Troubleshooting](#troubleshooting)
5. [After Code Updates](#after-code-updates)

---

## Quick Comparison

| Feature | start.sh | Systemd Service |
|---------|----------|-----------------|
| **Best For** | Testing, Development | Production |
| **Runs in Background** | ❌ No | ✅ Yes |
| **Auto-start on Boot** | ❌ No | ✅ Yes |
| **Auto-restart on Failure** | ❌ No | ✅ Yes |
| **Process Management** | Manual | Automatic |
| **Logs Location** | Terminal | Systemd journal + files |
| **Stop Method** | Ctrl+C | `sudo systemctl stop` |

---

## Method 1: Manual Start (start.sh)

### When to Use

- ✅ Testing the application
- ✅ Development and debugging
- ✅ Quick startup without systemd
- ✅ Seeing real-time output
- ❌ Not recommended for production

### Step-by-Step Instructions

#### 1. Navigate to Application Directory
```bash
cd ~/scoring_app
```

#### 2. Make Script Executable (if needed)
```bash
chmod +x start.sh
```

#### 3. Start the Application
```bash
./start.sh
```

### What Happens

The script will:
1. Activate the Python virtual environment
2. Load environment variables from `.env`
3. Create `data/` and `uploads/` directories if missing
4. Check if `data/sanskriti-3.xlsx` exists
5. Start Gunicorn with 4 workers
6. Display startup information

### Expected Output

```
Starting Flask application...
Host: 0.0.0.0
Port: 5000
Environment: production

Starting with Gunicorn...
[2026-01-26 12:00:00 +0000] [12345] [INFO] Starting gunicorn 20.1.0
[2026-01-26 12:00:00 +0000] [12345] [INFO] Listening at: http://0.0.0.0:5000 (12345)
[2026-01-26 12:00:00 +0000] [12345] [INFO] Using worker: sync
[2026-01-26 12:00:00 +0000] [12346] [INFO] Booting worker with pid: 12346
[2026-01-26 12:00:00 +0000] [12347] [INFO] Booting worker with pid: 12347
[2026-01-26 12:00:00 +0000] [12348] [INFO] Booting worker with pid: 12348
[2026-01-26 12:00:00 +0000] [12349] [INFO] Booting worker with pid: 12349
```

### Accessing the Application

Open your browser and navigate to:
```
http://your-vm-ip:5000
```

### Stopping the Application

Press `Ctrl+C` in the terminal where the application is running.

### Common Issues

**Issue: Port 5000 already in use**
```bash
# Find what's using the port
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>

# Or change port in .env
nano .env
# Change PORT=5000 to PORT=5001
```

**Issue: Permission denied**
```bash
chmod +x start.sh
```

**Issue: Virtual environment not found**
```bash
# Run deployment script first
./deploy.sh
```

**Issue: Excel file not found**
```bash
# Check if file exists
ls -lh data/sanskriti-3.xlsx

# If missing, copy it
scp sanskriti-3.xlsx username@vm-ip:~/scoring_app/data/
```

---

## Method 2: Systemd Service

### When to Use

- ✅ Production deployment
- ✅ Need background service
- ✅ Want auto-restart on failure
- ✅ Need auto-start on server reboot
- ✅ Better process management

### Step-by-Step Instructions

#### 1. Install the Service

```bash
cd ~/scoring_app
chmod +x install-service.sh
./install-service.sh
```

**What this does:**
- Creates systemd service file at `/etc/systemd/system/scoring-app.service`
- Configures service to run as your user
- Sets up logging directories
- Enables auto-restart on failure
- Reloads systemd daemon

**Expected Output:**
```
Installing systemd service...
Copying service file to /etc/systemd/system/...
Reloading systemd...
Enabling service...
Service installed successfully!

To start the service:
  sudo systemctl start scoring-app

To stop the service:
  sudo systemctl stop scoring-app

To check status:
  sudo systemctl status scoring-app

To view logs:
  sudo journalctl -u scoring-app -f
```

#### 2. Start the Service

```bash
sudo systemctl start scoring-app
```

#### 3. Enable Auto-Start on Boot

```bash
sudo systemctl enable scoring-app
```

This ensures the service starts automatically when the server reboots.

#### 4. Verify Service is Running

```bash
sudo systemctl status scoring-app
```

**Expected Output:**
```
● scoring-app.service - Contest Scoring System Flask Application
   Loaded: loaded (/etc/systemd/system/scoring-app.service; enabled; vendor preset: enabled)
   Active: active (running) since Mon 2026-01-26 12:00:00 UTC; 10s ago
 Main PID: 12345 (gunicorn)
    Tasks: 5 (limit: 4915)
   Memory: 150.0M
   CGroup: /system.slice/scoring-app.service
           ├─12345 /home/username/scoring_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000...
           ├─12346 /home/username/scoring_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000...
           ├─12347 /home/username/scoring_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000...
           └─12348 /home/username/scoring_app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000...

Jan 26 12:00:00 vm-hostname systemd[1]: Started Contest Scoring System Flask Application.
Jan 26 12:00:00 vm-hostname gunicorn[12345]: [INFO] Starting gunicorn 20.1.0
Jan 26 12:00:00 vm-hostname gunicorn[12345]: [INFO] Listening at: http://0.0.0.0:5000 (12345)
```

### Service Management Commands

#### Start Service
```bash
sudo systemctl start scoring-app
```

#### Stop Service
```bash
sudo systemctl stop scoring-app
```

#### Restart Service
```bash
# Use after code updates or configuration changes
sudo systemctl restart scoring-app
```

#### Reload Service
```bash
# Reload without stopping (if supported)
sudo systemctl reload scoring-app
```

#### Check Service Status
```bash
sudo systemctl status scoring-app
```

#### Check if Service is Active
```bash
sudo systemctl is-active scoring-app
# Output: active
```

#### Check if Service is Enabled (auto-start)
```bash
sudo systemctl is-enabled scoring-app
# Output: enabled
```

#### Disable Auto-Start
```bash
sudo systemctl disable scoring-app
```

#### Enable Auto-Start
```bash
sudo systemctl enable scoring-app
```

### Viewing Logs

#### Real-Time Logs (Follow Mode)
```bash
sudo journalctl -u scoring-app -f
```

Press `Ctrl+C` to exit follow mode.

#### Last N Lines
```bash
# Last 50 lines
sudo journalctl -u scoring-app -n 50

# Last 100 lines
sudo journalctl -u scoring-app -n 100
```

#### Logs Since Today
```bash
sudo journalctl -u scoring-app --since today
```

#### Logs Since Specific Time
```bash
sudo journalctl -u scoring-app --since "2026-01-26 10:00:00"
```

#### Logs Between Dates
```bash
sudo journalctl -u scoring-app --since "2026-01-26 00:00:00" --until "2026-01-26 23:59:59"
```

#### Application Log Files
```bash
# Access logs
tail -f ~/scoring_app/logs/access.log

# Error logs
tail -f ~/scoring_app/logs/error.log
```

### Accessing the Application

Once the service is running, access at:
```
http://your-vm-ip:5000
```

---

## Troubleshooting

### Service Won't Start

**1. Check Service Status:**
```bash
sudo systemctl status scoring-app
```

**2. Check Detailed Logs:**
```bash
sudo journalctl -u scoring-app -n 100 --no-pager
```

**3. Verify Service File:**
```bash
sudo systemctl cat scoring-app
```

**4. Check File Permissions:**
```bash
ls -la ~/scoring_app/
chmod +x ~/scoring_app/*.sh
```

### Service Starts But Immediately Stops

**1. Check Logs for Errors:**
```bash
sudo journalctl -u scoring-app -n 100 --no-pager
```

**2. Verify Excel File Exists:**
```bash
ls -lh ~/scoring_app/data/sanskriti-3.xlsx
```

**3. Test Manual Start:**
```bash
cd ~/scoring_app
source venv/bin/activate
python app.py
```

This will show errors that might not appear in systemd logs.

**4. Check Virtual Environment:**
```bash
ls -la ~/scoring_app/venv/bin/python
```

**5. Verify Environment Variables:**
```bash
cat ~/scoring_app/.env
```

### Permission Errors

**Fix Ownership:**
```bash
sudo chown -R $USER:$USER ~/scoring_app
```

**Fix Permissions:**
```bash
chmod +x ~/scoring_app/*.sh
chmod 644 ~/scoring_app/.env
chmod 755 ~/scoring_app/data
```

### Port Already in Use

**Find Process Using Port:**
```bash
sudo lsof -i :5000
```

**Kill the Process:**
```bash
sudo kill -9 <PID>
```

**Or Change Port:**
```bash
nano ~/scoring_app/.env
# Change: PORT=5000
# To: PORT=5001
sudo systemctl restart scoring-app
```

### Excel File Not Found

**Check File Location:**
```bash
ls -lh ~/scoring_app/data/sanskriti-3.xlsx
```

**Copy File if Missing:**
```bash
# From local machine
scp sanskriti-3.xlsx username@vm-ip:~/scoring_app/data/
```

**Verify Path in .env:**
```bash
grep EXCEL_FILE_PATH ~/scoring_app/.env
```

---

## After Code Updates

When you pull new code from GitHub:

### For Systemd Service:

```bash
cd ~/scoring_app

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart the service
sudo systemctl restart scoring-app

# Verify it's running
sudo systemctl status scoring-app
```

### For Manual Start:

```bash
cd ~/scoring_app

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Stop current instance (Ctrl+C) and restart
./start.sh
```

---

## Service Configuration Details

The systemd service is configured with:

- **Type**: `simple` - Service runs in foreground
- **User**: Your username (automatically detected)
- **Working Directory**: `~/scoring_app`
- **Environment File**: `~/scoring_app/.env`
- **ExecStart**: Gunicorn with 4 workers
- **Restart**: `always` - Auto-restart on failure
- **RestartSec**: `10` - Wait 10 seconds before restart
- **Logs**: 
  - Systemd journal: `sudo journalctl -u scoring-app`
  - Application logs: `~/scoring_app/logs/access.log` and `error.log`

---

## Quick Reference

### Start Application
```bash
# Manual
./start.sh

# Service
sudo systemctl start scoring-app
```

### Stop Application
```bash
# Manual
Ctrl+C

# Service
sudo systemctl stop scoring-app
```

### Restart Application
```bash
# Service only
sudo systemctl restart scoring-app
```

### Check Status
```bash
# Service only
sudo systemctl status scoring-app
```

### View Logs
```bash
# Service - Real-time
sudo journalctl -u scoring-app -f

# Service - Last 100 lines
sudo journalctl -u scoring-app -n 100

# Manual - Terminal output
# (Logs appear in terminal)
```

---

For more information, see [DEPLOYMENT.md](DEPLOYMENT.md)
