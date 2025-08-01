import os

# Secret key for session management
SECRET_KEY = 'your-secret-key-here'

# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///student_portal.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# File upload settings
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt', 'jpg', 'png', 'zip'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size