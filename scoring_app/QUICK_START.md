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

### 3. Update Configuration
Edit `.env` file and update the Excel file path:
```bash
nano .env
```

### 4. Upload Your Excel File
```bash
# From your local machine
scp sanskriti-3.xlsx username@vm-ip:~/scoring_app/data/
```

### 5. Start the Application

**Option A: Manual Start (Testing)**
```bash
./start.sh
```

**Option B: Systemd Service (Production)**
```bash
./install-service.sh
sudo systemctl start scoring-app
sudo systemctl enable scoring-app
```

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
