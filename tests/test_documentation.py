"""Keep localized release guides navigable and installation commands consistent."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ('en', 'ko', 'zh-CN', 'ja', 'es', 'fr')
PAGES = ('console', 'architecture', 'editions', 'migration', 'security')


def test_localized_documentation_links_and_setup():
  for language in LANGUAGES:
    readme = ROOT / ('README.md' if language == 'en' else f'README.{language}.md')
    documents = [readme, *(ROOT / 'docs' / language / f'{page}.md' for page in PAGES)]
    for document in documents:
      text = document.read_text()
      assert len(text) > 500, document
      for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
          continue
        assert (document.parent / target.split('#')[0]).is_file(), (document, target)
    guide = documents[1].read_text()
    for command in ('./scripts/install-console.sh', './scripts/run-console.sh', '127.0.0.1:5176'):
      assert command in guide and command in readme.read_text(), (language, command)
    for page in PAGES:
      text = (ROOT / 'docs' / language / f'{page}.md').read_text()
      for other in LANGUAGES:
        assert f'../{other}/{page}.md' in text
