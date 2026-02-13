# Nipoppy Copilot Instructions

This document provides guidance for AI coding agents working with the Nipoppy repository. Following these instructions will help you work efficiently and maintain code quality.

## Repository Overview

**Nipoppy** is a lightweight framework for standardized organization and processing of neuroimaging-clinical datasets. It helps users adopt FAIR principles and improve study reproducibility.

### Key Components

1. **Command-line interface (CLI)**: Python-based CLI tool (`nipoppy`) with commands for dataset initialization, BIDS conversion, processing, tracking, and extraction
2. **Python package**: Core library implementing workflows, configuration management, and data structures
3. **Pipeline framework**: Integration with containerized pipelines via Boutiques descriptors and Apptainer containers
4. **Documentation**: Sphinx-based documentation with tutorials, how-to guides, and API reference

### Technology Stack

- **Language**: Python 3.10+ (tested on 3.10, 3.11, 3.12, 3.13, 3.14)
- **Build system**: Hatch with VCS versioning
- **CLI framework**: rich-click (Rich + Click)
- **Configuration**: Pydantic models with JSON schemas
- **Testing**: pytest with pytest-xdist, pytest-cov, pytest-mock
- **Documentation**: Sphinx with MyST parser
- **Container runtime**: Apptainer (formerly Singularity)
- **Pipeline descriptors**: Boutiques framework

## Project Structure

```
nipoppy/
├── nipoppy/              # Main package
│   ├── cli/              # CLI commands and options
│   ├── config/           # Pydantic configuration models
│   ├── data/             # Template files, layouts, examples
│   ├── tabular/          # Data models for CSV/TSV files
│   ├── utils/            # Utility functions
│   └── workflows/        # Core workflow implementations
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # End-to-end tests
│   └── conftest.py       # Pytest fixtures
├── docs/                 # Sphinx documentation
│   ├── scripts/          # Doc build scripts
│   └── source/           # Documentation source files
├── pyproject.toml        # Project metadata and dependencies
├── .pre-commit-config.yaml  # Pre-commit hook configuration
└── .flake8               # Flake8 linting configuration
```

## Development Environment Setup

### Installation

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nipoppy.git
   cd nipoppy
   ```

2. **Create a dedicated Python environment** (Python 3.10+):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
   This installs all dependencies needed for development, testing, and documentation.

4. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Available Installation Extras

- `[test]` or `[tests]`: Testing dependencies
- `[doc]`: Documentation building dependencies
- `[dev]`: Development dependencies (includes test and doc)
- `[gui]` or `[tui]`: Terminal UI dependencies (Trogon)
- `[parallel]`: Parallel processing dependencies (joblib)

## Code Organization

### Main Modules

- **`nipoppy/cli/`**: CLI implementation
  - `cli.py`: Main CLI entry point with command groups
  - `options.py`: Shared CLI options and decorators
  - `pipeline_catalog.py`: Pipeline store commands

- **`nipoppy/config/`**: Configuration schemas (Pydantic models)
  - `main.py`: Main dataset configuration
  - `pipeline.py`: Pipeline configuration base classes
  - `boutiques.py`: Boutiques descriptor configuration
  - `container.py`: Container configuration
  - `hpc.py`: HPC/cluster configuration

- **`nipoppy/workflows/`**: Core workflow implementations
  - `base.py`: Base workflow class with common utilities
  - `dataset_init.py`: Dataset initialization
  - `dicom_reorg.py`: DICOM reorganization
  - `bids_conversion.py`: BIDS conversion
  - `processing_runner.py`: Pipeline processing
  - `tracker.py`: Processing status tracking
  - `extractor.py`: Feature extraction

- **`nipoppy/tabular/`**: Data models for tabular data
  - `manifest.py`: Participant manifest
  - `curation_status.py`: Data curation status
  - `processing_status.py`: Pipeline processing status
  - `dicom_dir_map.py`: DICOM directory mapping

### Key Design Patterns

1. **Pydantic models**: All configuration and tabular data uses Pydantic for validation
2. **Workflow base class**: All workflows inherit from `BaseWorkflow` in `workflows/base.py`
3. **Logging**: Uses a custom logger from `nipoppy.logger` with Rich formatting
4. **Path handling**: Uses `pathlib.Path` throughout; type hint `StrOrPathLike` accepts both str and Path
5. **Configuration loading**: JSON-based configuration files loaded and validated via Pydantic

## Testing

### Running Tests

The project uses pytest with several plugins for testing:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not api"              # Non-API tests (default in CI)
pytest -m "api"                  # API tests (requires credentials)
pytest -m "no_xdist"             # Tests that can't run in parallel

# Run specific test file or directory
pytest tests/unit/test_console.py
pytest tests/unit/workflows/

# Run with coverage
pytest --cov=nipoppy --cov-report=html

# Run specific test
pytest tests/unit/test_console.py::test_global_consoles -v
```

### Test Configuration

- **Location**: `tests/` directory with subdirectories for unit, integration, and e2e tests
- **Fixtures**: Defined in `tests/conftest.py`
- **Parallel execution**: Tests run in parallel by default using pytest-xdist
- **Markers**:
  - `api`: Tests that call external APIs (Zenodo)
  - `no_xdist`: Tests that should not run in parallel
- **Configuration**: Test settings in `[tool.pytest.ini_options]` section of `pyproject.toml`

### Test Organization

- **Unit tests** (`tests/unit/`): Test individual functions/classes in isolation
- **Integration tests** (`tests/integration/`): Test interactions between components
- **End-to-end tests** (`tests/e2e/`): Test complete workflows
- **Test data** (`tests/data/`): Sample data files for testing

### Important Test Notes

- Tests use pytest-xdist for parallel execution (`-n auto --dist loadfile`)
- Some tests are marked with `no_xdist` and must run sequentially (use `-n 0`)
- API tests require `ZENODO_TOKEN` and `ZENODO_ID` environment variables
- Mock objects from pytest-mock are used extensively for external dependencies

## Code Quality and Style

### Linting and Formatting

The project uses several tools to ensure code quality:

1. **black**: Code formatter (line length: 88)
2. **isort**: Import sorting (Black-compatible profile)
3. **flake8**: Linting with docstring checking (NumPy style)
4. **codespell**: Spell checking

### Running Linting Tools

```bash
# Run all pre-commit hooks on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run black --all-files
pre-commit run flake8 --all-files
pre-commit run isort --all-files

# Auto-format code
black nipoppy/ tests/
isort nipoppy/ tests/
```

### Code Style Guidelines

1. **Docstrings**: Use NumPy-style docstrings for all public functions/classes
2. **Type hints**: Use type hints for function signatures
3. **Line length**: Maximum 88 characters (Black default)
4. **Imports**: Organized with isort (standard library, third-party, local)
5. **Naming conventions**:
   - Classes: `PascalCase`
   - Functions/variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private members: Leading underscore `_private`

### Flake8 Configuration

Key flake8 settings in `.flake8`:
- Docstring convention: NumPy style
- Max complexity: 12
- Max function length: 150
- Ignore rules: D105 (magic method docstrings), E203 (slice notation), E704 (def/lambda statements)
- Per-file ignores for test files and `__init__.py`

## Documentation

### Building Documentation

Documentation uses Sphinx with MyST parser for Markdown support:

```bash
cd docs
make html
```

Built documentation is in `docs/build/html/index.html`.

### Documentation Notes

**⚠️ Known Issue**: Documentation build may fail in environments without internet access due to network requests for:
- Zenodo API calls in `conf.py`
- External link checking
- Schema generation that requires network resources

**Workaround**: If you encounter network-related errors during doc build, this is expected in sandboxed environments. The documentation builds successfully in environments with internet access (e.g., Read the Docs).

### Documentation Structure

- **Source files**: `docs/source/` (Markdown and RST)
- **API documentation**: Auto-generated from docstrings using sphinx-autoapi
- **CLI reference**: Generated from Click commands using sphinx-click
- **Schemas**: JSON schemas auto-generated from Pydantic models via `docs/scripts/pydantic_to_jsonschema.py`

### Documentation Extras

- MyST parser for Markdown support with extended syntax
- Sphinx Design for cards, tabs, and other components
- Furo theme for modern, responsive documentation
- Copybutton for code blocks
- GitHub changelog integration

## CI/CD Workflows

### GitHub Actions Workflows

1. **`run_tests.yml`**: Runs test suite on all supported Python versions
   - Triggers: Push, PR, daily schedule, manual dispatch
   - Runs non-API tests for all pushes
   - Runs API tests only on schedule/manual dispatch with Python 3.14
   - Uploads coverage to Codecov

2. **`build_and_publish.yml`**: Builds and publishes package
   - Builds on every push
   - Publishes to PyPI only on tag pushes
   - Creates GitHub releases with signed artifacts

3. **`linkcheck.yml`**: Checks documentation links

4. **Other workflows**: Label management, stale issue handling, citation file validation

### CI Testing Configuration

- Tests run in parallel using pytest-xdist
- Coverage reporting via Codecov
- Python versions: 3.10, 3.11, 3.12, 3.13, 3.14
- OS: Ubuntu latest

## Common Development Tasks

### Adding a New CLI Command

1. Add command function in appropriate file in `nipoppy/cli/`
2. Use `@click.command()` decorator with appropriate options
3. Register command in main CLI group in `cli.py`
4. Add integration test in `tests/integration/`
5. Update CLI documentation if needed

### Adding a New Workflow

1. Create new workflow class in `nipoppy/workflows/` inheriting from `BaseWorkflow`
2. Implement required abstract methods
3. Add workflow-specific configuration in `nipoppy/config/`
4. Add unit tests in `tests/unit/workflows/`
5. Update documentation with usage examples

### Adding a New Configuration Field

1. Update appropriate Pydantic model in `nipoppy/config/`
2. Add field with type hints and Field() descriptor
3. Update JSON schema examples in `nipoppy/data/`
4. Add unit tests for validation
5. Update documentation

### Adding Dependencies

1. Add to `dependencies` list in `pyproject.toml` for core dependencies
2. Add to appropriate `[project.optional-dependencies]` section for optional features
3. Consider version constraints (e.g., avoid known broken versions like `pybids!=0.18.0`)
4. Run `pip install -e ".[dev]"` to update local environment

## Common Pitfalls and Workarounds

### 1. Documentation Build Failures

**Issue**: Documentation build fails with network errors (httpx.ConnectError)

**Cause**: The documentation build process calls external APIs (Zenodo) and requires internet access

**Workaround**: This is expected in sandboxed/offline environments. The docs build successfully on Read the Docs and in environments with internet access. If working on documentation locally, you may need internet access or can comment out the network-dependent parts in `docs/source/conf.py`.

### 2. Test Parallelization Issues

**Issue**: Some tests fail when run in parallel with pytest-xdist

**Cause**: Tests that modify global state or shared resources

**Workaround**: Mark such tests with `@pytest.mark.no_xdist` and they will run sequentially. Run them separately with `-n 0`:
```bash
pytest -m "no_xdist" -n 0
```

### 3. Import Errors After Installation

**Issue**: Cannot import nipoppy modules after installation

**Cause**: Not installed in editable mode or wrong Python environment

**Workaround**: Ensure you install with `-e` flag: `pip install -e ".[dev]"`

### 4. Pre-commit Hook Failures

**Issue**: Pre-commit hooks fail on commit

**Cause**: Code doesn't meet formatting/linting standards

**Workaround**:
```bash
# Auto-fix most issues
pre-commit run --all-files

# Manually fix remaining issues flagged by flake8
# Then retry commit
```

### 5. Version File Not Found

**Issue**: `_version.py` file missing

**Cause**: Using VCS-based versioning (hatch-vcs)

**Workaround**: The version file is auto-generated during build. Ensure you have git history available. For development, the package auto-generates version from git tags.

### 6. Pydantic Validation Errors

**Issue**: Configuration loading fails with Pydantic validation errors

**Cause**: JSON config files don't match schema

**Workaround**: Check the JSON schema files in `docs/source/schemas/` or use the example files in `nipoppy/data/examples/`. Pydantic error messages indicate which fields are invalid.

### 7. Boutiques/Apptainer Dependencies

**Issue**: Tests or workflows fail related to containers

**Cause**: Apptainer/Singularity not available in environment

**Workaround**: Many tests mock container execution. If working with actual pipelines, you'll need Apptainer installed. For development/testing of non-container code, mocks are sufficient.

## Best Practices

### When Making Changes

1. **Create a feature branch** from main
2. **Write tests first** (TDD approach) or alongside code changes
3. **Run tests locally** before pushing: `pytest`
4. **Run linters** before committing: `pre-commit run --all-files`
5. **Keep changes focused** - one issue/feature per PR
6. **Update documentation** if changing user-facing features
7. **Follow existing code patterns** and style

### Code Review Expectations

- PRs are reviewed by maintainers
- CI must pass (tests, linting)
- Emoji in reviews:
  - 🧑‍🍳: Approved/ready to merge
  - 🍒: Optional suggestions (nice-to-have)
- Re-request review after addressing required changes

### Commit Messages

- Use clear, descriptive commit messages
- Reference issue numbers when applicable: `Fix #123: Description`
- Use conventional commit style when possible

### Testing Strategy

- **Write unit tests** for new functions/methods
- **Mock external dependencies** (file system, network, containers)
- **Use fixtures** from conftest.py for common test data
- **Aim for high coverage** of new code (project has >80% coverage)

## Additional Resources

- **Documentation**: https://nipoppy.readthedocs.io
- **GitHub Repository**: https://github.com/nipoppy/nipoppy
- **PyPI Package**: https://pypi.org/project/nipoppy/
- **Issue Tracker**: https://github.com/nipoppy/nipoppy/issues
- **Discord Community**: https://discord.gg/2VMKFRpjkm
- **Contributing Guide**: See `docs/source/contributing.md`

## Quick Reference

### Essential Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest                                    # All tests
pytest -m "not api"                      # Non-API tests
pytest tests/unit/                       # Unit tests only

# Code quality
pre-commit run --all-files               # All checks
black nipoppy/ tests/                    # Format code
flake8 nipoppy/                          # Lint code

# Documentation
cd docs && make html                     # Build docs

# CLI
nipoppy --help                           # CLI help
nipoppy COMMAND --help                   # Command help
```

### File Locations

- Main package: `nipoppy/`
- Tests: `tests/`
- Documentation: `docs/source/`
- Configuration: `pyproject.toml`, `.flake8`, `.pre-commit-config.yaml`
- Test data: `tests/data/`
- Template files: `nipoppy/data/`

---

**Note**: This document is maintained alongside the codebase. When making significant changes to development workflows or project structure, please update this file accordingly.
