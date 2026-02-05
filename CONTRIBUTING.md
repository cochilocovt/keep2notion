# Contributing to Keep2Notion

Thank you for your interest in contributing to Keep2Notion!

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/keep2notion.git
   cd keep2notion
   ```

3. Copy the environment template:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

5. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Use **Black** for Python formatting: `black .`
- Use **isort** for import sorting: `isort .`
- Follow **PEP 8** guidelines
- Add type hints where possible
- Write clear docstrings for functions and classes

## Testing

- Add tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Add/update tests
4. Update documentation if needed
5. Format code: `black . && isort .`
6. Commit with clear messages
7. Push to your fork
8. Submit a pull request

## Reporting Bugs

Use GitHub Issues with the bug template. Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Logs if applicable

## Feature Requests

Use GitHub Issues with the feature request template. Describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help maintain a positive community

## Questions?

Feel free to open an issue for questions or join discussions!
