"""
Pytest module to test xpedite features report and record with:
Application running in a REMOTE box, benchmarks and performance counters
This module also provides test for generating profile information and
a Jupyter notebook

This module contains pytests to test Xpedite features including:
1. Record
2. Report
3. Profile info generation
4. Probes
5. Jupyter notebook creation

Author:  Brooke Elizabeth Cantwell, Morgan Stanley
"""

import pytest
from test_xpedite.test_profiler.profile       import (
                                                runXpediteReport, runXpediteRecord, loadProbes,
                                                buildNotebook, compareVsBaseline
                                              )
from test_xpedite.test_profiler.comparator    import findDiff
from test_xpedite.test_profiler.context       import Context
from test_xpedite.test_profiler.scenario      import ScenarioLoader

CONTEXT = None
SCENARIO_LOADER = ScenarioLoader()

@pytest.fixture(autouse=True)
def setTestParameters(hostname, transactions, multithreaded, workspace, rundir, apps):
  """
  A method run at the beginning of tests to create and enter a REMOTE environment
  and at the end of tests to exit the REMOTE environment

 @param hostname: An option added to the pytest parser to accept a REMOTE host
                   Defaults to 127.0.0.1
  @type hostname: C{str}
  """
  from xpedite.util              import makeLogPath
  from xpedite.transport.net     import isIpLocal
  from xpedite.transport.remote  import Remote
  remote = None
  global CONTEXT # pylint: disable=global-statement
  if not isIpLocal(hostname):
    remote = Remote(hostname, makeLogPath('remote'))
    remote.__enter__()
  CONTEXT = Context(transactions, multithreaded, workspace)
  SCENARIO_LOADER.loadScenarios(rundir, apps, remote)

  yield
  if remote:
    remote.__exit__(None, None, None)

def test_report_vs_baseline():
  """
  Run xpedite report on a data file in the test directory, return profiles and compare
  the previously generated profiles from the same xpedite run
  """
  for scenarios in SCENARIO_LOADER:
    with scenarios as scenarios:
      compareVsBaseline(CONTEXT, scenarios)

def test_record_vs_report(capsys):
  """
  Run xpedite record and xpedite report to compare profiles
  """
  for scenarios in SCENARIO_LOADER:
    with scenarios as scenarios:
      with capsys.disabled():
        currentReport, _, _ = runXpediteRecord(CONTEXT, scenarios)
      report = runXpediteReport(currentReport.runId, CONTEXT, scenarios)
      findDiff(report.profiles.__dict__, currentReport.profiles.__dict__)
      assert report.profiles == currentReport.profiles

def test_generate_cmd_vs_baseline():
  """
  Test xpedite generate by generating a new profileInfo.py file and comparing to baseline
  profileInfo.py in the test data directory
  """
  from test_xpedite.test_profiler.app import TargetLauncher
  from xpedite.profiler.probeAdmin    import ProbeAdmin
  for scenarios in SCENARIO_LOADER:
    with scenarios as scenarios:
      with TargetLauncher(CONTEXT, scenarios) as app:
        generatedProfileInfo = scenarios.generateProfileInfo(app.xpediteApp)
      findDiff(generatedProfileInfo.__dict__, scenarios.baselineProfileInfo.__dict__)
      assert generatedProfileInfo == scenarios.baselineProfileInfo

def test_probe_states(capsys):
  """
  Test xpedite probes and probes state for an application's against baseline probe states
  for the application
  """
  import cPickle as pickle
  from xpedite.types.probe import compareProbes
  for scenarios in SCENARIO_LOADER:
    with scenarios as scenarios:
      probeMap = {}
      with capsys.disabled():
        probes = loadProbes(CONTEXT, scenarios)
        for probe in probes:
          probeMap[probe.sysName] = probe
      assert len(probes) == len(scenarios.baselineProbeMap.keys())
      findDiff(probeMap, scenarios.baselineProbeMap)
      for probe in probeMap.keys():
        assert compareProbes(probeMap[probe], scenarios.baselineProbeMap[probe])

def test_notebook_build(capsys):
  """
  Test to confirm a Jupyter notebook can be creating from profile information and results
  generated by xpedite record
  """
  for scenarios in SCENARIO_LOADER:
    with scenarios as scenarios:
      with capsys.disabled():
        notebook, _, report, _, _ = buildNotebook(CONTEXT, scenarios)
        assert len(report.categories) > 0
      assert notebook
