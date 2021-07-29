#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: jacobfaibussowitsch
"""

import os

class Runner(object):
  def __init__(self,*args):
    self.argList = list(args)
    self.setuptime = {}
    self.solvetime = {}
    self.itercount = {}
    return

  def parseOutput(self,out,device,smoother):
    import re

    refelems = re.compile('^Number of finite element unknowns: ([0-9]+)')
    refsetup = re.compile('^Setup time = ([0-9]+\.[0-9]+)')
    refsolve = re.compile('^Solve time = ([0-9]+\.[0-9]+)')
    refiter  = re.compile('\s+Iteration :\s+([0-9]+)')

    if smoother not in self.setuptime.keys():
      self.setuptime[smoother] = {}
    if smoother not in self.solvetime.keys():
      self.solvetime[smoother] = {}
    if smoother not in self.itercount.keys():
      self.itercount[smoother] = {}

    for line in out.split('\n'):
      elems = refelems.search(line)
      if elems:
        self.elems = elems.group(1)
        continue
      setuptime = refsetup.search(line)
      if setuptime:
        self.setuptime[smoother][device] = setuptime.group(1)
        continue
      solvetime = refsolve.search(line)
      if solvetime:
        self.solvetime[smoother][device] = solvetime.group(1)
        continue
      itercnt = refiter.search(line)
      if itercnt:
        cnt = itercnt.group(1)

    self.itercount[smoother][device] = cnt
    return

  def run(self):
    import subprocess

    for device in ['cpu','cuda']:
      argListBase = self.argList+['--device',device]
      for smoother in ['J','GS','DR']:
        argList = argListBase+['--smoother',smoother]
        argStr = ' '.join(argList)
        print('Running {}'.format(argStr),end='\t',flush=True)
        with subprocess.Popen(argList,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as runner:
          (out,err) = runner.communicate()
          assert not runner.returncode,'{} raised returncode {}:\nstdout: {}\nstderr:{}'.format(argStr,runner.returncode,out.decode(),err.decode())
        self.parseOutput(out.decode(),device,smoother)
        print('success')
    return

  def get(self):
    return {
      'setuptime' : self.setuptime,
      'solvetime' : self.solvetime,
      'itercount' : self.itercount,
      'elemcount' : self.elems,
      'arglist'   : self.argList,
    }


def main(exe,ordRange,refine,mesh,outFile):
  assert os.path.exists(exe), 'Could not find {}'.format(exe)
  assert os.path.exists(mesh), 'Could not find {}'.format(mesh)

  results = {}
  try:
    for order in ordRange:
      runner = Runner(exe,'-o',str(order),'-r',str(refine),'--mesh',mesh)
      runner.run()
      results[order] = runner.get()
  except AssertionError as ae:
    print(ae)
    print('\nsaving progress so far')

  with open(outFile,'w') as fd:
    import json
    print('Writing results to file:',outFile,end='\t')
    json.dump(results,fd)
    assert os.path.exists(outFile), '\nError writing results file {}'.format(outFile)
    print('success')
  return


if __name__ == '__main__':
  import argparse

  defaultOutput = 'output_o{ordmin}_{ordmax}_r{refine}.json'
  parser = argparse.ArgumentParser(description='Collect timing results for DRSmoothers',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('exec',help='path to example to time')
  parser.add_argument('-o','--order-range',metavar='int',default=[4,7],type=int,nargs=2,dest='ordrange')
  parser.add_argument('-r','--refine',metavar='int',default=0,type=int,dest='refine')
  parser.add_argument('-m','--mesh',default='../data/inline-hex.mesh')
  parser.add_argument('-t','--target',default=defaultOutput,help='path to output file')
  args = parser.parse_args()

  if args.target == defaultOutput:
    args.target = args.target.format(ordmin=args.ordrange[0],ordmax=args.ordrange[1],refine=args.refine)

  if not args.target.endswith('.json'):
    args.target += '.json'

  main(os.path.abspath(args.exec),range(*args.ordrange),args.refine,os.path.abspath(args.mesh),os.path.abspath(args.target))
