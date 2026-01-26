# Deployment Guide for VM

This guide will help you deploy the Contest Scoring System on a VM and run it from GitHub.

## Prerequisites

- A VM with Ubuntu/Debian Linux
- SSH access to the VM
- Git installed on the VM
- Python 3.8+ installed

## Step 1: Initial Setup on VM

### 1.1 Connect to your VM
```bash
ssh username@your-vm-ip
```

### 1.2 Clone the Repository
```bash
cd ~
git clone <your-github-repo-url> scoring_app
cd scoring_app
```

### 1.3 Run Deployment Script
```bash
chmod +x deploy.sh
./deploy.sh
```

This script will:
- Update system packages
- Install Python 3 and pip (if not installed)
- Install nginx (optional, for reverse proxy)
- Create virtual environment
- Install Python dependencies
- Set up environment variables
- Create necessary directories

## Step 2: Configure the Application

### 2.1 Update Environment Variables
Edit the `.env` file:
```bash
nano .env
```

Update the following variables:
```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
HOST=0.0.0.0
PORT=5000
EXCEL_FILE_PATH=/home/username/scoring_app/data/sanskriti-3.xlsx
UPLOAD_FOLDER=/home/username/scoring_app/uploads
DATA_FOLDER=/home/username/scoring_app/data
```

### 2.2 Upload Excel File
Place your Excel file in the data directory:
```bash
# From your local machine
scp sanskriti-3.xlsx username@your-vm-ip:~/scoring_app/data/
```

Or upload via SFTP/SCP to: `~/scoring_app/data/sanskriti-3.xlsx`

## Step 3: Start the Application

### Option A: Manual Start (for testing)
```bash
chmod +x start.sh
./start.sh
```

The application will be available at: `http://your-vm-ip:5000`

### Option B: Systemd Service (Recommended for production)

1. Install the systemd service:
```bash
chmod +x install-service.sh
./install-service.sh
```

2. Start the service:
```bash
sudo systemctl start scoring-app
```

3. Enable auto-start on boot:
```bash
sudo systemctl enable scoring-app
```

4. Check service status:
```bash
sudo systemctl status scoring-app
```

5. View logs:
```bash
# Real-time logs
sudo journalctl -u scoring-app -f

# Last 100 lines
sudo journalctl -u scoring-app -n 100
```

## Step 4: Configure Firewall

Allow traffic on port 5000:
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

## Step 5: Set Up Nginx Reverse Proxy (Optional but Recommended)

### 5.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/scoring-app
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your VM IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5.2 Enable the Site
```bash
sudo ln -s /etc/nginx/sites-available/scoring-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.3 Update Firewall
```bash
sudo ufw allow 'Nginx Full'
```

## Step 6: Update from GitHub

To pull the latest changes:
```bash
cd ~/scoring_app
git pull origin main  # or master
source venv/bin/activate
pip install -r requirements.txt

# Restart the service
sudo systemctl restart scoring-app
```

## Troubleshooting

### Application won't start
1. Check logs: `sudo journalctl -u scoring-app -n 50`
2. Verify virtual environment: `source venv/bin/activate && which python`
3. Check environment variables: `cat .env`
4. Verify file permissions: `ls -la ~/scoring_app`

### Port already in use
```bash
# Find process using port 5000
sudo lsof -i :5000
# Kill the process
sudo kill -9 <PID>
```

### Permission errors
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/scoring_app
# Fix permissions
chmod +x ~/scoring_app/*.sh
```

### Excel file not found
- Verify the file path in `.env`
- Check file exists: `ls -la ~/scoring_app/data/`
- Ensure file has correct permissions

## Service Management Commands

```bash
# Start service
sudo systemctl start scoring-app

# Stop service
sudo systemctl stop scoring-app

# Restart service
sudo systemctl restart scoring-app

# Check status
sudo systemctl status scoring-app

# View logs
sudo journalctl -u scoring-app -f

# Disable auto-start
sudo systemctl disable scoring-app
```

## Security Recommendations

1. **Change the SECRET_KEY** in `.env` to a strong random string
2. **Use HTTPS** with Let's Encrypt SSL certificate
3. **Set up firewall** rules to restrict access
4. **Regular backups** of the `data/` directory
5. **Keep system updated**: `sudo apt-get update && sudo apt-get upgrade`

## Backup

To backup your data:
```bash
# Create backup
tar -czf scoring-app-backup-$(date +%Y%m%d).tar.gz ~/scoring_app/data/

# Restore from backup
tar -xzf scoring-app-backup-YYYYMMDD.tar.gz -C ~/scoring_app/
```

## Monitoring

Monitor the application:
```bash
# Check if service is running
sudo systemctl is-active scoring-app

# Check resource usage
htop

# Check disk space
df -h
```

## Support

For issues or questions, check:
- Application logs: `~/scoring_app/logs/`
- System logs: `sudo journalctl -u scoring-app`
- Nginx logs: `/var/log/nginx/error.log`
