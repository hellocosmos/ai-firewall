"""Check current guide versions and repository/local landing link targets."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
CURRENT = ('self-hosting', 'aisg', 'providers', 'gateway-compatibility', 'deployment-fit', 'editions', 'console', 'architecture', 'identity')
errors = []
checked = 0


def anchors(path):
  text = path.read_text()
  if path.suffix == '.html':
    parser = Page(); parser.feed(text)
    return parser.ids
  ids, counts = set(), {}
  for heading in re.findall(r'^#{1,6}\s+(.+)$', re.sub(r'```.*?```', '', text, flags=re.S), re.M):
    slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
    number = counts.get(slug, 0); counts[slug] = number + 1
    ids.add(slug + (f'-{number}' if number else ''))
  return ids


class Page(HTMLParser):
  def __init__(self):
    super().__init__(); self.links = []; self.ids = set()
  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)
    if 'id' in attrs:self.ids.add(attrs['id'])
    key = 'href' if tag in ('a', 'link') else 'src' if tag in ('img', 'script') else None
    if key and key in attrs:self.links.append(attrs[key])


def check(target, source, landing=None):
  global checked
  url = urlsplit(target)
  prefix = '/hellocosmos/ai-security-gateway/blob/main/'
  if url.netloc == 'github.com' and url.path.startswith(prefix):
    path = ROOT / unquote(url.path[len(prefix):])
  elif url.scheme in ('mailto', 'tel') or (url.netloc and url.netloc != 'trapdefense.com'):
    return
  elif url.netloc == 'trapdefense.com' or (landing and source.suffix == '.html'):
    if landing is None:return
    path = landing / unquote(url.path.lstrip('/')) if url.path.startswith('/') else source.parent / unquote(url.path)
    if not url.path:path = source
    if path.is_dir():path = path / 'index.html'
  elif url.scheme:return
  else:
    path = source.parent / unquote(url.path) if url.path else source
  checked += 1
  if not path.is_file():errors.append(f'{source}: missing target {target}')
  elif url.fragment and path.suffix in ('.md', '.html') and unquote(url.fragment) not in anchors(path):
    errors.append(f'{source}: missing anchor {target}')


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--landing', type=Path)
args = parser.parse_args()
for document in [*ROOT.glob('README*.md'), *ROOT.glob('docs/*/*.md')]:
  text = document.read_text()
  if document.stem in CURRENT:
    # Current guides may cite history in their body, but must not lead with stale versions.
    for version in re.findall(r'\b0\.\d+\b', text.splitlines()[0]):
      if version != VERSION:errors.append(f'{document}: stale title version {version}')
    if re.search(r'^>.*\*\*0\.(?:39|40|41)', text, re.M):errors.append(f'{document}: stale feature banner')
  text = re.sub(r'```.*?```', '', text, flags=re.S)
  for target in re.findall(r'\]\(([^\s)]+)\)', text):check(target, document)
if args.landing:
  landing = args.landing.resolve()
  for name in ('index.html', 'docs/index.html', 'enterprise/index.html', 'thanks.html'):
    document = landing / name
    page = Page(); page.feed(document.read_text())
    for target in page.links:check(target, document, landing)
for error in errors:print(error)
print(f'Checked {checked} local/repository targets; {len(errors)} errors.')
sys.exit(bool(errors))
