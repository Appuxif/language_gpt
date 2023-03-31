import sys
from pathlib import Path

path = Path(__file__).parent.parent.parent

sys.path.append(str(path / 'src'))
sys.path.append(str(path / 'src' / 'project'))


def test():
    print('TEST')
