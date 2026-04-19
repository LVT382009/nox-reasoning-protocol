# Contributing to NOX Reasoning Protocol

Thank you for your interest in contributing to NOX! This document provides guidelines and instructions for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Description**: Clear and concise description of the bug
- **Reproduction Steps**: Steps to reproduce the behavior
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python version, NOX version
- **Screenshots/Logs**: If applicable

### Suggesting Enhancements

We welcome enhancement suggestions! Please include:

- **Problem Description**: What problem would this enhancement solve?
- **Proposed Solution**: How would you like to solve it?
- **Alternatives**: What alternatives have you considered?
- **Additional Context**: Any other context or screenshots

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- GitHub account

### Setting Up Development Environment

```bash
# Fork the repository
# Clone your fork
git clone https://github.com/YOUR_USERNAME/nox-reasoning-protocol.git
cd nox-reasoning-protocol

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## 📝 Code Style

### Python Code Style

- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Maximum line length: 120 characters
- Use type hints where appropriate
- Add docstrings to all functions and classes

### Example

```python
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result from a validation check.
    
    Attributes:
        passed: Whether the validation passed
        score: Confidence score (0-100)
        issues: List of issues found
    """
    passed: bool
    score: float
    issues: list
    metadata: Dict[str, Any] = None
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_validate.py
```

### Writing Tests

- Write tests for new features
- Maintain test coverage above 80%
- Use descriptive test names
- Include edge cases and error conditions

## 📚 Documentation

### Updating Documentation

- Keep README.md up to date with new features
- Update SPEC.md for architectural changes
- Add examples to SKILL.md for new functionality
- Update CHANGELOG.md for version changes

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep it beginner-friendly

## 🔄 Pull Request Process

### Before Submitting

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Run tests** and ensure they pass
6. **Commit your changes** with clear messages

### Commit Message Format

Follow conventional commits:

```
feat: add new validation template
fix: resolve timeout issue in layer 2
docs: update README with new examples
test: add tests for circular reasoning detection
chore: update dependencies
```

### Creating Pull Request

1. Push your changes to your fork
2. Create a pull request to the main repository
3. Fill in the PR template
4. Wait for review and address feedback

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No merge conflicts
```

## 🎯 Areas of Contribution

We're particularly interested in contributions in these areas:

### High Priority
- Additional validation templates
- Performance optimizations
- Bug fixes
- Test coverage improvements

### Medium Priority
- Documentation improvements
- New rule patterns
- Integration examples

### Low Priority
- UI improvements
- Tooling enhancements
- Experimental features

## 📋 Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainers review your PR
3. **Feedback**: Address any comments or suggestions
4. **Approval**: PR is approved and merged

## 🏆 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors list

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Email**: levantam.98.2324@gmail.com

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to NOX! 🎉
