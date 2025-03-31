# humanoid-retargeting
Retargeting motion from human to humanoid robots.

## Installation
```bash
conda create -n humanoid-retargeting python=3.10
conda activate humanoid-retargeting
pip install -e ../humanoid-robot-description
pip install -e .
```
## Usage
data path: `~/.humanoid_retargeting`

## Test
To show test coverage:
```bash
pytest --cov=humanoid_retargeting --cov-report=html
```
then open `htmlcov/index.html` in a web browser.