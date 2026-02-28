# Contributing to GM-AI-Hub / GM-AI-Hub에 기여하기

Thank you for your interest in contributing! This project was built by a citizen
of Gwangmyeong for public officers everywhere. Every contribution makes local
government AI more accessible.

GM-AI-Hub에 관심을 가져주셔서 감사합니다! 이 프로젝트는 광명시의 한 시민이
모든 공무원을 위해 만들었습니다. 모든 기여가 지방자치단체 AI를 더 가깝게
만듭니다.

---

## Getting Started / 시작하기

```bash
# Clone the repository
git clone https://github.com/durume/GM.git
cd GM

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Run tests
pytest

# Start development servers
python -m backend.main          # Backend on port 8080
npm run dev --prefix frontend   # Frontend on port 5173
```

## What You Can Contribute / 기여할 수 있는 것

### Code
- Bug fixes and performance improvements
- New AI pipelines for government document types
- Frontend UI/UX improvements
- Accessibility improvements
- Test coverage

### Localization
- Translate the UI to other languages (currently Korean only)
- Adapt document templates for other countries' government formats
- Translate documentation

### Documentation
- Improve setup guides for different environments
- Write tutorials for specific use cases
- Add inline code comments

### Data
- Contribute public regulation datasets for other cities
- Add example templates for different document types

## Guidelines / 가이드라인

### Code Style
- **Python**: Follow ruff defaults (configured in `pyproject.toml`)
- **JavaScript/JSX**: Standard React patterns, functional components
- **Commits**: Clear, concise messages in English or Korean
- **Comments**: Korean comments in backend code are fine (project convention)

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Submit a PR with a clear description

### Issues
- Use GitHub Issues for bug reports and feature requests
- Include steps to reproduce for bugs
- Include screenshots for UI issues

## Architecture Notes / 아키텍처 참고

Before making changes, please read:
- [CLAUDE.md](CLAUDE.md) — Project structure and conventions
- [WALKTHROUGH.md](WALKTHROUGH.md) — Detailed architecture walkthrough

Key patterns:
- **Backend routes** use try/except ImportError in `backend/api/router.py`
- **Frontend pages** are lazy-loaded via `React.lazy()`
- **AI pipelines** use DSPy in `backend/ai/pipelines/`
- **All data stays local** — never add external API calls for user data

## License / 라이선스

By contributing, you agree that your contributions will be licensed under the
[GM-Social License v1.0](LICENSE).

## Social Gratitude / 사회적 감사

If you deploy a fork or derivative, remember the Social Gratitude condition:
share a kind word about Gwangmyeong (광명) and discover the city on social media.
See [GRATITUDE.md](GRATITUDE.md) for details.

---

*Built with love in Gwangmyeong (광명), Gyeonggi-do.*
