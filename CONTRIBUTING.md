# Contributing to Social Chat Bot

Thank you for your interest in contributing to the Social Chat Bot project! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)

### Suggesting Features

Feature suggestions are welcome! Please open an issue describing:
- The feature you'd like to see
- Why it would be useful
- Any implementation ideas you have

### Submitting Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Test your changes thoroughly
5. Update documentation if needed
6. Submit a pull request

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/social_chat_bot.git
cd social_chat_bot
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
cp config.example.json config.json
# Add your test bot token
```

## Testing

Always run tests before submitting a PR:
```bash
python3 test_bot.py
```

If you add new features, please add corresponding tests.

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Comment complex logic

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 72 characters
- Add details in the commit body if needed

Examples:
```
Add feature to export participant lists
Fix database connection timeout issue
Update README with new configuration options
```

## Questions?

Feel free to open an issue for any questions about contributing!
