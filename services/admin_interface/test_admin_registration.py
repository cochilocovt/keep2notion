"""Test script to verify Django admin registration."""

import os
import sys
import django

# Add the admin_interface directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_project.settings')
django.setup()

from django.contrib import admin
from sync_admin.models import SyncJob, SyncState, Credential, SyncLog


def test_admin_registration():
    """Test that all models are registered with Django admin."""
    print("Testing Django admin registration...")
    
    # Get all registered models
    registered_models = admin.site._registry
    
    # Test 1: Check SyncJob is registered
    assert SyncJob in registered_models, "SyncJob not registered in admin"
    print("✓ SyncJob is registered in admin")
    
    # Test 2: Check SyncState is registered
    assert SyncState in registered_models, "SyncState not registered in admin"
    print("✓ SyncState is registered in admin")
    
    # Test 3: Check Credential is registered
    assert Credential in registered_models, "Credential not registered in admin"
    print("✓ Credential is registered in admin")
    
    # Test 4: Check SyncLog is registered
    assert SyncLog in registered_models, "SyncLog not registered in admin"
    print("✓ SyncLog is registered in admin")
    
    # Test 5: Check admin classes have proper configuration
    sync_job_admin = registered_models[SyncJob]
    assert hasattr(sync_job_admin, 'list_display'), "SyncJobAdmin missing list_display"
    assert 'job_id' in sync_job_admin.list_display, "job_id not in list_display"
    print("✓ SyncJobAdmin has proper configuration")
    
    sync_state_admin = registered_models[SyncState]
    assert hasattr(sync_state_admin, 'list_display'), "SyncStateAdmin missing list_display"
    print("✓ SyncStateAdmin has proper configuration")
    
    credential_admin = registered_models[Credential]
    assert hasattr(credential_admin, 'list_display'), "CredentialAdmin missing list_display"
    print("✓ CredentialAdmin has proper configuration")
    
    sync_log_admin = registered_models[SyncLog]
    assert hasattr(sync_log_admin, 'list_display'), "SyncLogAdmin missing list_display"
    assert hasattr(sync_log_admin, 'message_preview'), "SyncLogAdmin missing message_preview method"
    print("✓ SyncLogAdmin has proper configuration")
    
    print("\n" + "="*50)
    print("All admin registration tests passed!")
    print("="*50)


if __name__ == '__main__':
    try:
        test_admin_registration()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
