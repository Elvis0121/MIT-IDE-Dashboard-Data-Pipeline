# Contributing to MIT IDE Dashboard

Thank you for your interest in contributing to the MIT IDE Dashboard project! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by the MIT Code of Conduct.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the Issues section
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Check if the feature has already been suggested in the Issues section
2. If not, create a new issue with:
   - A clear, descriptive title
   - Detailed description of the feature
   - Use cases and benefits
   - Any implementation ideas you have

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Run the test suite
7. Submit a pull request

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/mit-ide-dashboard.git
cd mit-ide-dashboard
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused
- Write docstrings for all functions and classes

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Run tests with:
```bash
pytest
```

### Documentation

- Update README.md if needed
- Add docstrings to new functions/classes
- Update .env.example if adding new environment variables
- Document any API changes

## Review Process

1. All PRs will be reviewed by maintainers
2. Changes may be requested
3. Once approved, your PR will be merged

## Questions?

Feel free to open an issue for any questions about contributing. 