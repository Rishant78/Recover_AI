import sys
import os

# Add Backend folder to the system path so Python can find 'app' module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Backend'))

from app.main import app
