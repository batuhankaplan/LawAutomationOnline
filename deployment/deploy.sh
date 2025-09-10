#!/bin/bash
#
# LawAutomation Deployment Script
# This script sets up the application on a fresh Ubuntu server
#

set -e  # Exit on error

echo "========================================="
echo "LawAutomation Deployment Script"
echo "========================================="

# Variables
APP_DIR="/var/www/lawautomation"
REPO_URL="https://github.com/yourusername/lawautomation.git"  # Update this
DOMAIN="yourdomain.com"  # Update this
EMAIL="your-email@example.com"  # Update this for Let's Encrypt

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   exit 1
fi

# Step 1: Update system
print_status "Updating system packages..."
apt-get update && apt-get upgrade -y

# Step 2: Install required packages
print_status "Installing required packages..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    postgresql \
    postgresql-contrib \
    git \
    supervisor \
    certbot \
    python3-certbot-nginx \
    build-essential \
    python3.11-dev \
    libpq-dev \
    ufw

# Step 3: Setup firewall
print_status "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Step 4: Create application directory
print_status "Creating application directory..."
mkdir -p $APP_DIR
mkdir -p /var/log/lawautomation
mkdir -p /var/www/lawautomation/uploads

# Step 5: Clone repository (or copy files)
print_status "Setting up application files..."
# Option 1: Clone from git
# git clone $REPO_URL $APP_DIR

# Option 2: Copy from local (if deploying from local machine)
# rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' ./ $APP_DIR/

# Step 6: Setup Python virtual environment
print_status "Setting up Python virtual environment..."
cd $APP_DIR
python3.11 -m venv venv
source venv/bin/activate

# Step 7: Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install psycopg2-binary  # For PostgreSQL

# Step 8: Setup PostgreSQL database
print_status "Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE USER lawautomation WITH PASSWORD 'your-secure-password';
CREATE DATABASE lawautomation OWNER lawautomation;
GRANT ALL PRIVILEGES ON DATABASE lawautomation TO lawautomation;
EOF

# Step 9: Create .env file
print_status "Creating environment configuration..."
cat > $APP_DIR/.env <<EOF
FLASK_ENV=production
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=postgresql://lawautomation:your-secure-password@localhost/lawautomation
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
UPLOAD_FOLDER=/var/www/lawautomation/uploads/
EOF

# Step 10: Initialize database
print_status "Initializing database..."
cd $APP_DIR/firstwebsite
source ../venv/bin/activate
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Step 11: Set permissions
print_status "Setting permissions..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
chmod 600 $APP_DIR/.env

# Step 12: Setup Gunicorn
print_status "Setting up Gunicorn..."
cp $APP_DIR/gunicorn_config.py /etc/
cp $APP_DIR/deployment/lawautomation.service /etc/systemd/system/

# Step 13: Setup Nginx
print_status "Setting up Nginx..."
cp $APP_DIR/deployment/nginx.conf /etc/nginx/sites-available/lawautomation
ln -sf /etc/nginx/sites-available/lawautomation /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Update domain in nginx config
sed -i "s/yourdomain.com/$DOMAIN/g" /etc/nginx/sites-available/lawautomation

# Step 14: Start services
print_status "Starting services..."
systemctl daemon-reload
systemctl enable lawautomation
systemctl start lawautomation
systemctl restart nginx

# Step 15: Setup SSL with Let's Encrypt
print_status "Setting up SSL certificate..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL

# Step 16: Setup log rotation
print_status "Setting up log rotation..."
cat > /etc/logrotate.d/lawautomation <<EOF
/var/log/lawautomation/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload lawautomation
    endscript
}
EOF

# Step 17: Create admin user
print_status "Creating admin user..."
cd $APP_DIR/firstwebsite
source ../venv/bin/activate
python -c "
from app import app, db
from models import User
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@lawautomation.com',
            first_name='Admin',
            last_name='User',
            phone='0000000000',
            role='Yönetici Avukat',
            is_admin=True,
            is_approved=True
        )
        admin.set_password('ChangeThisPassword123!')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
"

print_status "========================================="
print_status "Deployment completed successfully!"
print_status "========================================="
echo ""
print_warning "IMPORTANT NEXT STEPS:"
echo "1. Update the admin password immediately"
echo "2. Configure your DNS to point to this server"
echo "3. Update email settings in .env file"
echo "4. Test the application at https://$DOMAIN"
echo ""
print_status "To check application status: systemctl status lawautomation"
print_status "To view logs: journalctl -u lawautomation -f"
