"""Run synthetic by default; live calls require an explicit model and private key file."""
import argparse
import json
from pathlib import Path
from .stack import execute

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',default=None)
parser.add_argument('--provider-key-file',type=Path)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
if args.provider_key_file and not args.model:parser.error('Live mode requires --model')
if args.report.exists():parser.error('Choose a new report path; existing evidence is preserved')
try:
  result=execute(args.model or 'synthetic-model',args.provider_key_file)
except Exception as error:
  # Do not expose model bodies, request headers, SDK exception payloads or credentials.
  parser.exit(1,'Workflow verification failed ('+type(error).__name__+'). No successful report written.\n')
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(result,indent=2)+'\n')
print('PASS: report written to '+str(args.report))
