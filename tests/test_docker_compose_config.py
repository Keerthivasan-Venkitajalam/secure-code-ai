"""
Test docker-compose configuration for local testing.
Validates the docker-compose.yml structure and settings.
"""

import os
import yaml
import pytest
from pathlib import Path


@pytest.fixture
def docker_compose_path():
    """Get path to docker-compose.yml."""
    project_root = Path(__file__).parent.parent
    compose_path = project_root / "deployment" / "docker-compose.yml"
    return compose_path


@pytest.fixture
def docker_compose_config(docker_compose_path):
    """Load docker-compose.yml configuration."""
    with open(docker_compose_path, 'r') as f:
        return yaml.safe_load(f)


def test_docker_compose_file_exists(docker_compose_path):
    """Test that docker-compose.yml exists."""
    assert docker_compose_path.exists(), "docker-compose.yml not found"


def test_docker_compose_version(docker_compose_config):
    """Test that docker-compose version is specified."""
    assert 'version' in docker_compose_config
    assert docker_compose_config['version'] in ['3.8', '3.9', '3']


def test_secureai_api_service_defined(docker_compose_config):
    """Test that secureai-api service is defined."""
    assert 'services' in docker_compose_config
    assert 'secureai-api' in docker_compose_config['services']


def test_service_build_configuration(docker_compose_config):
    """Test that service has proper build configuration."""
    service = docker_compose_config['services']['secureai-api']
    
    # Check build context
    assert 'build' in service
    assert 'context' in service['build']
    assert service['build']['context'] == '..'
    
    # Check Dockerfile path
    assert 'dockerfile' in service['build']
    assert 'Dockerfile' in service['build']['dockerfile']


def test_service_port_mapping(docker_compose_config):
    """Test that port 8000 is exposed."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'ports' in service
    assert len(service['ports']) > 0
    
    # Check that port 8000 is mapped
    port_mappings = service['ports']
    has_8000 = any('8000' in str(port) for port in port_mappings)
    assert has_8000, "Port 8000 not exposed"


def test_environment_variables_set(docker_compose_config):
    """Test that required environment variables are set."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'environment' in service
    env_vars = service['environment']
    
    # Convert list format to dict for easier checking
    env_dict = {}
    for env in env_vars:
        if isinstance(env, str) and '=' in env:
            key, value = env.split('=', 1)
            env_dict[key] = value
    
    # Check required environment variables
    required_vars = [
        'SECUREAI_HOST',
        'SECUREAI_PORT',
        'SECUREAI_MODEL_PATH',
        'SECUREAI_LOG_LEVEL',
        'SECUREAI_ENABLE_DOCS',
    ]
    
    for var in required_vars:
        assert var in env_dict, f"Required environment variable {var} not set"


def test_models_volume_mounted(docker_compose_config):
    """Test that models directory is mounted as persistent volume."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'volumes' in service
    volumes = service['volumes']
    
    # Check that /models is mounted
    has_models_mount = any('/models' in str(vol) for vol in volumes)
    assert has_models_mount, "Models directory not mounted"


def test_code_directories_mounted(docker_compose_config):
    """Test that local code directories are mounted for development."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'volumes' in service
    volumes = service['volumes']
    
    # Check that api and agent directories are mounted
    has_api_mount = any('/app/api' in str(vol) for vol in volumes)
    has_agent_mount = any('/app/agent' in str(vol) for vol in volumes)
    
    assert has_api_mount, "API directory not mounted"
    assert has_agent_mount, "Agent directory not mounted"


def test_persistent_volume_defined(docker_compose_config):
    """Test that persistent volume for models is defined."""
    assert 'volumes' in docker_compose_config
    volumes = docker_compose_config['volumes']
    
    # Check that models volume is defined
    assert 'models-data' in volumes or 'models' in volumes


def test_health_check_configured(docker_compose_config):
    """Test that health check is configured."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'healthcheck' in service
    healthcheck = service['healthcheck']
    
    # Check health check configuration
    assert 'test' in healthcheck
    assert 'interval' in healthcheck
    assert 'timeout' in healthcheck
    assert 'retries' in healthcheck
    
    # Verify health check tests the /health endpoint
    test_cmd = ' '.join(healthcheck['test'])
    assert '/health' in test_cmd


def test_restart_policy_set(docker_compose_config):
    """Test that restart policy is configured."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'restart' in service
    assert service['restart'] in ['unless-stopped', 'always', 'on-failure']


def test_container_name_set(docker_compose_config):
    """Test that container has a name."""
    service = docker_compose_config['services']['secureai-api']
    
    assert 'container_name' in service
    assert service['container_name'] == 'secureai-api'


def test_model_configuration_variables(docker_compose_config):
    """Test that model configuration variables are set."""
    service = docker_compose_config['services']['secureai-api']
    env_vars = service['environment']
    
    # Convert to dict
    env_dict = {}
    for env in env_vars:
        if isinstance(env, str) and '=' in env:
            key, value = env.split('=', 1)
            env_dict[key] = value
    
    # Check model-specific variables
    model_vars = [
        'SECUREAI_MODEL_PATH',
        'SECUREAI_MODEL_NAME',
        'SECUREAI_MODEL_QUANTIZATION',
    ]
    
    for var in model_vars:
        assert var in env_dict, f"Model configuration variable {var} not set"


def test_workflow_configuration_variables(docker_compose_config):
    """Test that workflow configuration variables are set."""
    service = docker_compose_config['services']['secureai-api']
    env_vars = service['environment']
    
    # Convert to dict
    env_dict = {}
    for env in env_vars:
        if isinstance(env, str) and '=' in env:
            key, value = env.split('=', 1)
            env_dict[key] = value
    
    # Check workflow-specific variables
    workflow_vars = [
        'SECUREAI_MAX_ITERATIONS',
        'SECUREAI_SYMBOT_TIMEOUT',
    ]
    
    for var in workflow_vars:
        assert var in env_dict, f"Workflow configuration variable {var} not set"


def test_logging_configuration_variables(docker_compose_config):
    """Test that logging configuration variables are set."""
    service = docker_compose_config['services']['secureai-api']
    env_vars = service['environment']
    
    # Convert to dict
    env_dict = {}
    for env in env_vars:
        if isinstance(env, str) and '=' in env:
            key, value = env.split('=', 1)
            env_dict[key] = value
    
    # Check logging-specific variables
    logging_vars = [
        'SECUREAI_LOG_LEVEL',
        'SECUREAI_LOG_FORMAT',
    ]
    
    for var in logging_vars:
        assert var in env_dict, f"Logging configuration variable {var} not set"


def test_env_example_file_exists():
    """Test that .env.example file exists."""
    project_root = Path(__file__).parent.parent
    env_example_path = project_root / "deployment" / ".env.example"
    
    assert env_example_path.exists(), ".env.example file not found"


def test_docker_compose_documentation_exists():
    """Test that docker-compose documentation exists."""
    project_root = Path(__file__).parent.parent
    docs_path = project_root / "deployment" / "DOCKER_COMPOSE.md"
    
    assert docs_path.exists(), "DOCKER_COMPOSE.md documentation not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
