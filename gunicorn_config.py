"""
Gunicorn configuration file for production
"""
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = '/var/log/lawautomation/gunicorn_access.log'
errorlog = '/var/log/lawautomation/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'lawautomation'

# Server mechanics
daemon = False
pidfile = '/var/run/lawautomation.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'
