# Setting Up GitHub Repository

This guide walks you through creating and pushing the Loop Health repository to GitHub.

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Fill in:
   - **Repository name**: `loop-health`
   - **Description**: `Adaptive Loop-Breaking Protocol for Deterministic Self-Play`
   - **Public** (recommended for open research)
   - **Add .gitignore**: Already included
   - **Add LICENSE**: MIT (already included)

3. Click "Create repository"

## Step 2: Initialize Git Locally

The repository at `g:\loop-health` is ready to push. Just initialize git:

```bash
cd g:\loop-health
git init
git add .
git commit -m "Initial commit: Loop Health framework with Chess domain validation"
```

## Step 3: Connect to GitHub

```bash
git remote add origin https://github.com/NikolasAng/loop-health.git
git branch -M main
git push -u origin main
```

## Step 4: Verify on GitHub

Visit https://github.com/NikolasAng/loop-health and verify:
- ✓ All files present
- ✓ README.md renders correctly
- ✓ Code files are visible
- ✓ .gitignore is active

## Step 5: Update Paper Reference

In `paper.tex`, update the GitHub reference:
- Old: https://github.com/NikolasAng/loop-health-games (outdated)
- New: https://github.com/NikolasAng/loop-health ✓

The paper already references the correct URL.

## Repository Structure

```
loop-health/
├── README.md                    # Main documentation
├── LICENSE                      # MIT License
├── setup.py                     # Package installation
├── requirements.txt             # Dependencies
├── .gitignore                   # Exclude unnecessary files
│
├── loop_health/                 # Core framework
│   ├── loop_health.py          # Main algorithm
│   ├── chess_engine.py         # Chess-specific engine
│   ├── chess_game.py           # Chess domain wrapper
│   ├── features.py             # Feature extractors
│   ├── game.py                 # Base game abstraction
│   └── __init__.py
│
├── games/
│   └── chess/                  # Chess domain
│       ├── chess_null_model.py           # Permutation testing (validation)
│       ├── live_chess_demo.py            # Real-time CST-Lazy demo
│       ├── selfplay_detection_chess.py   # Self-play attractor analysis
│       └── __init__.py
│
├── examples/
│   ├── basic_usage.py          # Usage examples
│   └── __init__.py
│
├── docs/
│   ├── ARCHITECTURE.md         # Technical architecture
│   └── __init__.py
│
└── tests/                       # Unit tests (future)
```

## Installing from GitHub

Users can install with:

```bash
git clone https://github.com/NikolasAng/loop-health.git
cd loop-health
pip install -r requirements.txt
```

Or directly from PyPI (after packaging):

```bash
pip install loop-health
```

## Running Demonstrations

After installation:

```bash
# Basic null model testing (validates framework)
cd games/chess
python chess_null_model.py

# Real-time stagnation detection
python live_chess_demo.py

# Self-play attractor analysis
python selfplay_detection_chess.py

# Simple usage example
cd ../../examples
python basic_usage.py
```

## Publishing to PyPI (Optional)

To make the package pip-installable globally:

```bash
pip install twine
python setup.py sdist bdist_wheel
twine upload dist/*
```

Then users can:
```bash
pip install loop-health
```

## GitHub Actions (Optional)

Create `.github/workflows/test.yml` for automated testing:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/
```

## Documentation (Optional)

Create `docs/` for hosted documentation on Read the Docs:

1. Go to https://readthedocs.org
2. Connect GitHub repository
3. Build automatically on push

## Versioning

Current: v1.0.0 (as defined in `setup.py`)

Update after releases:
```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

## Citation

Users can cite with:

```bibtex
@software{angelosoulis2025loophealth,
  title={Loop Health Framework},
  author={Angelosoulis, Nikolaos},
  url={https://github.com/NikolasAng/loop-health},
  year={2025},
  version={1.0.0}
}
```

## Next Steps

1. ✓ Create repository on GitHub
2. ✓ Push from `g:\loop-health`
3. ✓ Verify files visible
4. ✓ Update paper.tex (already done: https://github.com/NikolasAng/loop-health)
5. ✓ Run demo from GitHub (test downstream users can install)
6. ✓ Submit paper with GitHub link

## Troubleshooting

### Git not found
- Install Git for Windows: https://git-scm.com/download/win
- Restart terminal

### Authentication issues
- Use personal access token instead of password
- GitHub → Settings → Developer settings → Personal access tokens
- Use token in place of password

### Large files
- If any CSV/PGN files >100MB, consider Git LFS
- `git lfs install` then `git lfs track "*.csv"`

---

**Status**: Repository structure complete and ready for GitHub
**Next Action**: Create repository on GitHub, then push from local machine
