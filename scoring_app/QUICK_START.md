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
