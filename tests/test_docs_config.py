"""
Tests for API documentation configuration.
Tests that documentation endpoints can be disabled via environment variable.
"""

import pytest
import os
from fastapi.testclient import TestClient


def test_docs_enabled_by_default():
    """Test that documentation is enabled by default."""
    # Import after setting env var
    from api.server import app
    
    client = TestClient(app)
    
    # Check that /docs is accessible
    response = client.get("/docs")
    assert response.status_code == 200, "Docs should be accessible by default"
    
    # Check that /redoc is accessible
    response = client.get("/redoc")
    assert response.status_code == 200, "ReDoc should be accessible by default"
    
    # Check that OpenAPI schema is accessible
    response = client.get("/openapi.json")
    assert response.status_code == 200, "OpenAPI schema should be accessible"


def test_docs_can_be_disabled():
    """
    Test that documentation can be disabled via SECUREAI_ENABLE_DOCS environment variable.
    
    Validates: Requirements 8.5
    """
    # Set environment variable to disable docs
    original_value = os.environ.get("SECUREAI_ENABLE_DOCS")
    os.environ["SECUREAI_ENABLE_DOCS"] = "false"
    
    try:
        # Force reload of config and app
        import importlib
        import api.config
        import api.server
        
        importlib.reload(api.config)
        importlib.reload(api.server)
        
        from api.server import app
        from api.config import config
        
        # Verify config is set correctly
        assert config.enable_docs is False, "Config should have enable_docs=False"
        
        # Verify app has docs disabled
        assert app.docs_url is None, "App should have docs_url=None"
        assert app.redoc_url is None, "App should have redoc_url=None"
        
        client = TestClient(app)
        
        # Check that /docs returns 404
        response = client.get("/docs")
        assert response.status_code == 404, "Docs should return 404 when disabled"
        
        # Check that /redoc returns 404
        response = client.get("/redoc")
        assert response.status_code == 404, "ReDoc should return 404 when disabled"
        
        # Check that OpenAPI schema is still accessible (for programmatic access)
        response = client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI schema should still be accessible"
        
    finally:
        # Restore original environment variable
        if original_value is not None:
            os.environ["SECUREAI_ENABLE_DOCS"] = original_value
        else:
            os.environ.pop("SECUREAI_ENABLE_DOCS", None)
        
        # Reload modules to restore original state
        import importlib
        import api.config
        import api.server
        
        importlib.reload(api.config)
        importlib.reload(api.server)


def test_docs_enabled_with_true_value():
    """Test that documentation is enabled when SECUREAI_ENABLE_DOCS=true."""
    # Set environment variable to enable docs
    original_value = os.environ.get("SECUREAI_ENABLE_DOCS")
    os.environ["SECUREAI_ENABLE_DOCS"] = "true"
    
    try:
        # Force reload of config and app
        import importlib
        import api.config
        import api.server
        
        importlib.reload(api.config)
        importlib.reload(api.server)
        
        from api.server import app
        from api.config import config
        
        # Verify config is set correctly
        assert config.enable_docs is True, "Config should have enable_docs=True"
        
        # Verify app has docs enabled
        assert app.docs_url == "/docs", "App should have docs_url='/docs'"
        assert app.redoc_url == "/redoc", "App should have redoc_url='/redoc'"
        
        client = TestClient(app)
        
        # Check that /docs is accessible
        response = client.get("/docs")
        assert response.status_code == 200, "Docs should be accessible when enabled"
        
        # Check that /redoc is accessible
        response = client.get("/redoc")
        assert response.status_code == 200, "ReDoc should be accessible when enabled"
        
    finally:
        # Restore original environment variable
        if original_value is not None:
            os.environ["SECUREAI_ENABLE_DOCS"] = original_value
        else:
            os.environ.pop("SECUREAI_ENABLE_DOCS", None)
        
        # Reload modules to restore original state
        import importlib
        import api.config
        import api.server
        
        importlib.reload(api.config)
        importlib.reload(api.server)


def test_root_endpoint_reflects_docs_status():
    """Test that root endpoint shows correct docs status."""
    from api.server import app
    from api.config import config
    
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "endpoints" in data
    
    # Check that docs endpoint status matches config
    if config.enable_docs:
        assert data["endpoints"]["docs"] == "/docs"
        assert data["endpoints"]["redoc"] == "/redoc"
    else:
        assert data["endpoints"]["docs"] == "disabled"
        assert data["endpoints"]["redoc"] == "disabled"
