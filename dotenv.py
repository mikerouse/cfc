"""
Minimal dotenv implementation for testing
"""
import os

def load_dotenv(path=None):
    """Load environment variables from .env file"""
    if path is None:
        path = '.env'
    
    if not os.path.exists(path):
        return
        
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()