"""Test script to verify Django project setup."""

import os
import sys
import django

# Add the admin_interface directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_project.settings')
django.setup()

from django.conf import settings
from django.core.management import call_command


def test_django_setup():
    """Test that Django is properly configured."""
    print("Testing Django setup...")
    
    # Test 1: Check settings are loaded
    print(f"✓ Django settings loaded")
    print(f"  - DEBUG: {settings.DEBUG}")
    print(f"  - Database engine: {settings.DATABASES['default']['ENGINE']}")
    print(f"  - Installed apps: {len(settings.INSTALLED_APPS)}")
    
    # Test 2: Check sync_admin app is installed
    assert 'sync_admin' in settings.INSTALLED_APPS, "sync_admin app not installed"
    print(f"✓ sync_admin app is installed")
    
    # Test 3: Check rest_framework is installed
    assert 'rest_framework' in settings.INSTALLED_APPS, "rest_framework not installed"
    print(f"✓ rest_framework is installed")
    
    # Test 4: Check templates directory is configured
    assert len(settings.TEMPLATES) > 0, "No templates configured"
    template_dirs = settings.TEMPLATES[0]['DIRS']
    assert len(template_dirs) > 0, "No template directories configured"
    print(f"✓ Templates directory configured: {template_dirs[0]}")
    
    # Test 5: Check static files configuration
    assert settings.STATIC_URL == '/static/', "STATIC_URL not configured correctly"
    assert settings.STATIC_ROOT is not None, "STATIC_ROOT not configured"
    print(f"✓ Static files configured")
    print(f"  - STATIC_URL: {settings.STATIC_URL}")
    print(f"  - STATIC_ROOT: {settings.STATIC_ROOT}")
    
    # Test 6: Check service URLs are configured
    assert hasattr(settings, 'SYNC_SERVICE_URL'), "SYNC_SERVICE_URL not configured"
    print(f"✓ Service URLs configured")
    print(f"  - SYNC_SERVICE_URL: {settings.SYNC_SERVICE_URL}")
    
    # Test 7: Check logging is configured
    assert 'version' in settings.LOGGING, "Logging not configured"
    print(f"✓ Logging configured")
    
    # Test 8: Run Django system check
    print("\nRunning Django system check...")
    call_command('check', verbosity=0)
    print("✓ Django system check passed")
    
    print("\n" + "="*50)
    print("All tests passed! Django project is properly configured.")
    print("="*50)


if __name__ == '__main__':
    try:
        test_django_setup()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
