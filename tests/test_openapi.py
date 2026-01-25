"""
Property-Based Tests for OpenAPI Schema Completeness
Tests that the OpenAPI schema includes all required metadata and examples.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from api.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_openapi_schema_exists(client):
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


def test_openapi_metadata_completeness(client):
    """
    Property 14: OpenAPI Schema Completeness
    For any API endpoint defined in the FastAPI application, the generated OpenAPI 3.0 schema
    should include request/response examples, parameter descriptions, and error response schemas.
    
    Validates: Requirements 8.3, 8.4
    Feature: backend-api-deployment, Property 14: OpenAPI Schema Completeness
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # Check OpenAPI version
    assert schema["openapi"].startswith("3."), "Should use OpenAPI 3.0+"
    
    # Check info metadata
    info = schema["info"]
    assert "title" in info, "Schema should have title"
    assert "description" in info, "Schema should have description"
    assert "version" in info, "Schema should have version"
    assert len(info["title"]) > 0, "Title should not be empty"
    assert len(info["description"]) > 0, "Description should not be empty"
    
    # Check tags are defined
    assert "tags" in schema, "Schema should define tags"
    assert len(schema["tags"]) > 0, "Should have at least one tag"
    
    # Verify each tag has name and description
    for tag in schema["tags"]:
        assert "name" in tag, f"Tag should have name: {tag}"
        assert "description" in tag, f"Tag {tag.get('name')} should have description"
    
    # Check paths exist
    paths = schema["paths"]
    assert len(paths) > 0, "Should have at least one endpoint"
    
    # Define expected endpoints
    expected_endpoints = ["/", "/analyze", "/health", "/health/ready"]
    
    for endpoint in expected_endpoints:
        assert endpoint in paths, f"Endpoint {endpoint} should be in schema"
    
    # Check /analyze endpoint completeness
    analyze_path = paths["/analyze"]
    assert "post" in analyze_path, "/analyze should have POST method"
    
    analyze_post = analyze_path["post"]
    
    # Check basic metadata
    assert "summary" in analyze_post, "/analyze should have summary"
    assert "description" in analyze_post, "/analyze should have description"
    assert "tags" in analyze_post, "/analyze should have tags"
    
    # Check request body
    assert "requestBody" in analyze_post, "/analyze should have requestBody"
    request_body = analyze_post["requestBody"]
    assert "content" in request_body, "Request body should have content"
    assert "application/json" in request_body["content"], "Should accept JSON"
    
    # Check request body has schema
    json_content = request_body["content"]["application/json"]
    assert "schema" in json_content, "Request body should have schema"
    
    # Check responses
    assert "responses" in analyze_post, "/analyze should have responses"
    responses = analyze_post["responses"]
    
    # Check success response (200)
    assert "200" in responses, "/analyze should have 200 response"
    success_response = responses["200"]
    assert "description" in success_response, "200 response should have description"
    assert "content" in success_response, "200 response should have content"
    assert "application/json" in success_response["content"], "200 response should be JSON"
    
    # Check that 200 response has examples
    success_content = success_response["content"]["application/json"]
    assert "example" in success_content or "examples" in success_content, \
        "200 response should have examples"
    
    # Check error responses
    expected_error_codes = ["400", "429", "500", "503"]
    for error_code in expected_error_codes:
        assert error_code in responses, f"/analyze should have {error_code} response"
        error_response = responses[error_code]
        assert "description" in error_response, f"{error_code} response should have description"
        assert "content" in error_response, f"{error_code} response should have content"
        
        # Check error response has example
        if "application/json" in error_response["content"]:
            error_content = error_response["content"]["application/json"]
            assert "example" in error_content or "examples" in error_content, \
                f"{error_code} response should have examples"


def test_health_endpoints_schema_completeness(client):
    """Test that health endpoints have complete schema documentation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    paths = schema["paths"]
    
    # Check /health endpoint
    assert "/health" in paths, "/health should be in schema"
    health_path = paths["/health"]
    assert "get" in health_path, "/health should have GET method"
    
    health_get = health_path["get"]
    assert "summary" in health_get, "/health should have summary"
    assert "description" in health_get, "/health should have description"
    assert "responses" in health_get, "/health should have responses"
    
    # Check /health has response examples
    health_responses = health_get["responses"]
    assert "200" in health_responses, "/health should have 200 response"
    
    health_200 = health_responses["200"]
    assert "content" in health_200, "/health 200 response should have content"
    if "application/json" in health_200["content"]:
        health_content = health_200["content"]["application/json"]
        assert "example" in health_content or "examples" in health_content, \
            "/health should have response examples"
    
    # Check /health/ready endpoint
    assert "/health/ready" in paths, "/health/ready should be in schema"
    ready_path = paths["/health/ready"]
    assert "get" in ready_path, "/health/ready should have GET method"
    
    ready_get = ready_path["get"]
    assert "summary" in ready_get, "/health/ready should have summary"
    assert "description" in ready_get, "/health/ready should have description"
    assert "responses" in ready_get, "/health/ready should have responses"
    
    # Check /health/ready has response examples
    ready_responses = ready_get["responses"]
    assert "200" in ready_responses, "/health/ready should have 200 response"
    
    ready_200 = ready_responses["200"]
    assert "content" in ready_200, "/health/ready 200 response should have content"
    if "application/json" in ready_200["content"]:
        ready_content = ready_200["content"]["application/json"]
        assert "example" in ready_content or "examples" in ready_content, \
            "/health/ready should have response examples"


def test_request_models_have_descriptions(client):
    """Test that all request model fields have descriptions."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # Get components/schemas
    assert "components" in schema, "Schema should have components"
    assert "schemas" in schema["components"], "Components should have schemas"
    
    schemas = schema["components"]["schemas"]
    
    # Check AnalyzeRequest schema
    assert "AnalyzeRequest" in schemas, "Should have AnalyzeRequest schema"
    analyze_request = schemas["AnalyzeRequest"]
    
    assert "properties" in analyze_request, "AnalyzeRequest should have properties"
    properties = analyze_request["properties"]
    
    # Check each property has description
    for prop_name, prop_schema in properties.items():
        assert "description" in prop_schema, \
            f"AnalyzeRequest.{prop_name} should have description"
        assert len(prop_schema["description"]) > 0, \
            f"AnalyzeRequest.{prop_name} description should not be empty"


def test_response_models_have_descriptions(client):
    """Test that all response model fields have descriptions."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    schemas = schema["components"]["schemas"]
    
    # Check response models
    response_models = [
        "AnalyzeResponse",
        "HealthResponse",
        "ReadinessResponse",
        "VulnerabilityResponse",
        "PatchResponse"
    ]
    
    for model_name in response_models:
        assert model_name in schemas, f"Should have {model_name} schema"
        model_schema = schemas[model_name]
        
        assert "properties" in model_schema, f"{model_name} should have properties"
        properties = model_schema["properties"]
        
        # Check each property has description
        for prop_name, prop_schema in properties.items():
            assert "description" in prop_schema, \
                f"{model_name}.{prop_name} should have description"
            assert len(prop_schema["description"]) > 0, \
                f"{model_name}.{prop_name} description should not be empty"


@given(
    endpoint=st.sampled_from(["/", "/analyze", "/health", "/health/ready"])
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_all_endpoints_have_tags(endpoint):
    """
    Property test: All endpoints should have tags for grouping.
    
    For any endpoint in the API, the OpenAPI schema should include tags
    for proper documentation grouping.
    """
    # Create client inside test to avoid fixture issues
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    paths = schema["paths"]
    assert endpoint in paths, f"Endpoint {endpoint} should exist"
    
    endpoint_schema = paths[endpoint]
    
    # Get the first HTTP method for this endpoint
    methods = [m for m in endpoint_schema.keys() if m in ["get", "post", "put", "delete", "patch"]]
    assert len(methods) > 0, f"Endpoint {endpoint} should have at least one HTTP method"
    
    method_schema = endpoint_schema[methods[0]]
    assert "tags" in method_schema, f"Endpoint {endpoint} {methods[0].upper()} should have tags"
    assert len(method_schema["tags"]) > 0, f"Endpoint {endpoint} should have at least one tag"


@given(
    http_method=st.sampled_from(["get", "post"]),
    endpoint=st.sampled_from(["/", "/analyze", "/health", "/health/ready"])
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_endpoints_have_summary_and_description(http_method, endpoint):
    """
    Property test: All endpoints should have summary and description.
    
    For any endpoint and HTTP method combination, the OpenAPI schema should include
    both summary and description fields.
    """
    # Create client inside test to avoid fixture issues
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    paths = schema["paths"]
    
    # Skip if endpoint doesn't exist or doesn't have this method
    if endpoint not in paths:
        return
    
    endpoint_schema = paths[endpoint]
    if http_method not in endpoint_schema:
        return
    
    method_schema = endpoint_schema[http_method]
    
    # Check summary and description exist
    assert "summary" in method_schema, \
        f"Endpoint {endpoint} {http_method.upper()} should have summary"
    assert "description" in method_schema, \
        f"Endpoint {endpoint} {http_method.upper()} should have description"
    
    # Check they are not empty
    assert len(method_schema["summary"]) > 0, \
        f"Endpoint {endpoint} {http_method.upper()} summary should not be empty"
    assert len(method_schema["description"]) > 0, \
        f"Endpoint {endpoint} {http_method.upper()} description should not be empty"
