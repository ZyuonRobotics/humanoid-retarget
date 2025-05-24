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

## Pipeline

### Aligner
- 根据robot_foot和human_foot修正机器人和人形的高度
- 获取机器人和人形的neck高度，用于计算

最终每个body的缩放比例：global_body_ratio * extra_body_ratio * relative_body_ratio_dict[body_name]

## Test
To show test coverage:
```bash
pytest --cov=humanoid_retargeting --cov-report=html
```
then open `htmlcov/index.html` in a web browser.