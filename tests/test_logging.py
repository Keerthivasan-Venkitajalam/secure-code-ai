"""
Unit and property tests for structured logging.
Tests JSON logging format, request context, and log completeness.
"""

import pytest
import json
import io
import sys
from unittest.mock import patch, Mock
from hypothesis import given, strategies as st
from loguru import logger

from api.logging_config import (
    configure_logging,
    set_request_context,
    clear_request_context,
    get_request_context,
    serialize_log_record
)


class TestLoggingConfiguration:
    """Test logging configuration."""
    
    def test_configure_logging_sets_up_handler(self):
        """Test configure_logging sets up log handler."""
        # Remove existing handlers
        logger.remove()
        
        # Configure logging
        configure_logging()
        
        # Verify handler was added (logger._core.handlers should not be empty)
        assert len(logger._core.handlers) > 0
    
    def test_request_context_management(self):
        """Test request context can be set and retrieved."""
        # Clear any existing context
        clear_request_context()
        
        # Set context
        set_request_context(
            request_id="test-123",
            code_length=100,
            file_path="test.py"
        )
        
        # Retrieve context
        context = get_request_context()
        
        assert context["request_id"] == "test-123"
        assert context["code_length"] == 100
        assert context["file_path"] == "test.py"
        
        # Clear context
        clear_request_context()
        context = get_request_context()
        assert context == {}
    
    def test_request_context_with_additional_fields(self):
        """Test request context accepts additional fields."""
        clear_request_context()
        
        set_request_context(
            request_id="test-456",
            custom_field="custom_value",
            another_field=42
        )
        
        context = get_request_context()
        assert context["request_id"] == "test-456"
        assert context["custom_field"] == "custom_value"
        assert context["another_field"] == 42
        
        clear_request_context()


class TestStructuredLogging:
    """Test structured logging output."""
    
    def test_log_record_serialization(self):
        """Test log record is serialized to JSON."""
        # Create mock log record
        from datetime import datetime
        
        # Create a simple level object
        class Level:
            def __init__(self, name):
                self.name = name
        
        record = {
            "time": datetime(2025, 1, 24, 12, 30, 45),
            "level": Level("INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "line": 42,
            "exception": None,
            "extra": {}
        }
        
        # Serialize
        json_str = serialize_log_record(record)
        
        # Parse JSON
        log_entry = json.loads(json_str)
        
        # Verify structure
        assert "timestamp" in log_entry
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Test message"
        assert log_entry["module"] == "test_module"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 42
    
    def test_log_record_includes_request_context(self):
        """Test log record includes request context."""
        from datetime import datetime
        
        class Level:
            def __init__(self, name):
                self.name = name
        
        # Set request context
        set_request_context(
            request_id="test-789",
            code_length=200
        )
        
        record = {
            "time": datetime(2025, 1, 24, 12, 30, 45),
            "level": Level("INFO"),
            "message": "Test with context",
            "name": "test_module",
            "function": "test_function",
            "line": 42,
            "exception": None,
            "extra": {}
        }
        
        # Serialize
        json_str = serialize_log_record(record)
        log_entry = json.loads(json_str)
        
        # Verify context is included
        assert "context" in log_entry
        assert log_entry["context"]["request_id"] == "test-789"
        assert log_entry["context"]["code_length"] == 200
        
        clear_request_context()
    
    def test_log_record_includes_exception_info(self):
        """Test log record includes exception information."""
        from datetime import datetime
        
        class Level:
            def __init__(self, name):
                self.name = name
        
        # Create mock exception
        try:
            raise ValueError("Test error")
        except ValueError as e:
            class ExceptionInfo:
                def __init__(self, exc):
                    self.type = type(exc)
                    self.value = exc
                    self.traceback = "mock traceback"
            
            exception_info = ExceptionInfo(e)
        
        record = {
            "time": datetime(2025, 1, 24, 12, 30, 45),
            "level": Level("ERROR"),
            "message": "Error occurred",
            "name": "test_module",
            "function": "test_function",
            "line": 42,
            "exception": exception_info,
            "extra": {}
        }
        
        # Serialize
        json_str = serialize_log_record(record)
        log_entry = json.loads(json_str)
        
        # Verify exception info
        assert "exception" in log_entry
        assert log_entry["exception"]["type"] == "ValueError"
        assert "Test error" in log_entry["exception"]["value"]
    
    def test_log_record_includes_extra_fields(self):
        """Test log record includes extra fields."""
        from datetime import datetime
        
        class Level:
            def __init__(self, name):
                self.name = name
        
        record = {
            "time": datetime(2025, 1, 24, 12, 30, 45),
            "level": Level("INFO"),
            "message": "Test with extras",
            "name": "test_module",
            "function": "test_function",
            "line": 42,
            "exception": None,
            "extra": {
                "execution_time": 15.3,
                "vulnerabilities_found": 2
            }
        }
        
        # Serialize
        json_str = serialize_log_record(record)
        log_entry = json.loads(json_str)
        
        # Verify extra fields
        assert log_entry["execution_time"] == 15.3
        assert log_entry["vulnerabilities_found"] == 2


# Property-Based Tests
@given(
    request_id=st.text(min_size=1, max_size=100),
    code_length=st.integers(min_value=0, max_value=1000000),
    file_path=st.text(min_size=1, max_size=200)
)
def test_property_structured_logging(request_id, code_length, file_path):
    """
    Property 7: Structured Logging
    
    Feature: backend-api-deployment, Property 7: Structured Logging
    Validates: Requirements 7.2, 7.5
    
    For any API request processed, the logs should contain JSON-formatted entries
    with timestamp, log_level, request_id, code_length, and execution_time fields.
    """
    from datetime import datetime
    
    class Level:
        def __init__(self, name):
            self.name = name
    
    # Set request context
    set_request_context(
        request_id=request_id,
        code_length=code_length,
        file_path=file_path
    )
    
    # Create log record
    record = {
        "time": datetime.now(),
        "level": Level("INFO"),
        "message": "Test message",
        "name": "test_module",
        "function": "test_function",
        "line": 42,
        "exception": None,
        "extra": {"execution_time": 10.5}
    }
    
    # Serialize
    json_str = serialize_log_record(record)
    
    # Parse JSON (should not raise exception)
    log_entry = json.loads(json_str)
    
    # Verify required fields are present
    assert "timestamp" in log_entry
    assert "level" in log_entry
    assert "message" in log_entry
    
    # Verify request context is included
    assert "context" in log_entry
    assert log_entry["context"]["request_id"] == request_id
    assert log_entry["context"]["code_length"] == code_length
    assert log_entry["context"]["file_path"] == file_path
    
    # Verify execution_time from extra fields
    assert log_entry["execution_time"] == 10.5
    
    clear_request_context()


@given(
    message=st.text(min_size=1, max_size=500),
    level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
)
def test_property_log_json_format(message, level):
    """
    Property 7: Structured Logging (JSON format validation)
    
    Feature: backend-api-deployment, Property 7: Structured Logging
    Validates: Requirements 7.2, 7.5
    
    For any log message and level, the serialized log should be valid JSON
    and contain all required fields.
    """
    from datetime import datetime
    
    class Level:
        def __init__(self, name):
            self.name = name
    
    record = {
        "time": datetime.now(),
        "level": Level(level),
        "message": message,
        "name": "test_module",
        "function": "test_function",
        "line": 42,
        "exception": None,
        "extra": {}
    }
    
    # Serialize
    json_str = serialize_log_record(record)
    
    # Should be valid JSON
    log_entry = json.loads(json_str)
    
    # Verify structure
    assert isinstance(log_entry, dict)
    assert log_entry["level"] == level
    assert log_entry["message"] == message
    assert "timestamp" in log_entry
    assert "module" in log_entry
    assert "function" in log_entry
    assert "line" in log_entry
