"""Run local MCP verification, optionally with an explicitly selected real LLM."""
import argparse
import asyncio
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import sys
from .harness import Pilot
from .verify import run_suite, verify_outage
from asr_proxy.inspection.pool import atomic_write


async def run(args):
  with Pilot(args.state_dir) as pilot:
    result={'version':importlib.metadata.version('trapdefense-ai-firewall'),
      'environment':{'os':platform.system(),'python':platform.python_version(),'mcp':importlib.metadata.version('mcp')},
      'model':{'evidence':'not_run','reason':'No explicit local model endpoint/name supplied'}}
    if args.model_url:
      from .agent import run_model_suite
      result['model']=await run_model_suite(pilot,args.model_url,args.model)
    result['protocol']=await run_suite(pilot,args.samples)
    result['protocol']['cases'].append(await verify_outage(pilot))
    atomic_write(pilot.directory/'report.json',json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 2 if args.model_url and any(t['status']!='model_finished' for t in result['model']['tasks']) else 0


def main():
  parser=argparse.ArgumentParser(description='Real MCP pilot; synthetic documents, no application SDK')
  parser.add_argument('--state-dir',type=Path,required=True,help='New private directory; never overwritten')
  parser.add_argument('--samples',type=int,choices=range(5,201),default=20,metavar='5..200')
  parser.add_argument('--model-url',help='Explicit local OpenAI-compatible http://127.0.0.1:PORT/v1 endpoint')
  parser.add_argument('--model',help='Model name; no automatic selection or scripted fallback')
  args=parser.parse_args()
  if bool(args.model_url)!=bool(args.model):parser.error('--model-url and --model must be supplied together')
  logging.disable(logging.CRITICAL)
  try:raise SystemExit(asyncio.run(run(args)))
  except (Exception,KeyboardInterrupt):
    print('Pilot incomplete. Check private logs and prerequisites; no success report was generated.',file=sys.stderr)
    raise SystemExit(1) from None


if __name__=='__main__':main()
