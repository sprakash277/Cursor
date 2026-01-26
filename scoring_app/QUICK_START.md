# Quick Start Guide - VM Deployment

## Quick Deployment Steps

### 1. On Your VM, Clone the Repository
```bash
cd ~
git clone <your-github-repo-url> scoring_app
cd scoring_app
```

### 2. Run Deployment Script
```bash
chmod +x deploy.sh
./deploy.sh
```

### 3. Upload Your Excel File to data/ folder
```bash
# From your local machine
scp sanskriti-3.xlsx username@vm-ip:~/scoring_app/data/
```

The Excel file must be placed at: `~/scoring_app/data/sanskriti-3.xlsx`

### 4. Verify Configuration (Optional)
The `.env` file is already configured to use the data/ folder. You can verify:
```bash
cat .env | grep -E "EXCEL_FILE_PATH|DATA_FOLDER"
```

Should show:
- `EXCEL_FILE_PATH=/home/username/scoring_app/data/sanskriti-3.xlsx`
- `DATA_FOLDER=/home/username/scoring_app/data`

### 5. Start the Application

#### Option A: Manual Start with start.sh (Testing/Development)

**Quick Start:**
```bash
./start.sh
```

**What it does:**
- Starts the app in your terminal
- Uses Gunicorn production server
- Shows real-time output
- Press `Ctrl+C` to stop

**When to use:**
- Testing the application
- Development and debugging
- Quick startup

**Access:** `http://your-vm-ip:5000`

---

#### Option B: Systemd Service (Production - Recommended)

**Install and Start:**
```bash
# 1. Install the service
./install-service.sh

# 2. Start the service
sudo systemctl start scoring-app

# 3. Enable auto-start on boot
sudo systemctl enable scoring-app

# 4. Check status
sudo systemctl status scoring-app
```

**What it does:**
- Runs as background service
- Auto-starts on server reboot
- Auto-restarts on failure
- Better for production use

**Service Management:**
```bash
# Start
sudo systemctl start scoring-app

# Stop
sudo systemctl stop scoring-app

# Restart (after code updates)
sudo systemctl restart scoring-app

# View logs
sudo journalctl -u scoring-app -f

# Check status
sudo systemctl status scoring-app
```

**When to use:**
- Production deployment
- Need background service
- Want auto-restart on failure
- Need auto-start on boot

**Access:** `http://your-vm-ip:5000`

**For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md) - Step 3**

### 6. Access the Application
Open browser: `http://your-vm-ip:5000`

## Update from GitHub
```bash
cd ~/scoring_app
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart scoring-app
```

## Check Status
```bash
sudo systemctl status scoring-app
```

## View Logs
```bash
sudo journalctl -u scoring-app -f
```

For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)
