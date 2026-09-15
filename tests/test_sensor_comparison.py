import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_sensor_pilot import compare_progress

class SensorComparisonTest(unittest.TestCase):
    def test_technical_error_does_not_become_paired_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); baseline=root/'clean';out=root/'sensor'
            settings={'task_id':0,'seed':0,'steps':220,'initial_state_ids':[0,1],
                      'condition':'clean','policy':{}}
            spec={'name':'brightness_shift','start_step':30,'duration_steps':30,'factor':.35}
            out.mkdir();(out/'protocol.json').write_text(json.dumps({'conditions':[spec]}))
            folder=out/'brightness_shift';folder.mkdir()
            ds=dict(settings,condition='brightness_shift',disturbance=spec)
            (folder/'manifest.json').write_text(json.dumps({'settings':ds}))
            def save(parent,state,condition,termination,success,steps,disturbance=None):
                path=parent/f'state-{state:02d}/attempt-01';path.mkdir(parents=True)
                (path/'report.json').write_text(json.dumps({
                    'task_id':0,'seed':0,'requested_steps':220,'initial_state_id':state,
                    'condition':condition,'disturbance':disturbance,'policy':{},
                    'termination':termination,'success':success,'completed_steps':steps,
                    'latencies_seconds':[1.5]*steps}))
            for state in [0,1]: save(baseline,state,'clean','success',True,80)
            save(folder,0,'brightness_shift','step_limit',False,220,spec)
            save(folder,1,'brightness_shift','error',False,69,spec)
            result=compare_progress(out,baseline,settings)['conditions']['brightness_shift']
            self.assertEqual(result['paired_completed'],1)
            self.assertEqual(result['lost_clean_successes'],1)
            self.assertEqual(result['pending'],1)
            self.assertEqual(result['task_failures'],1)
            self.assertEqual(result['technical_error_attempts'],1)
            self.assertEqual(result['paired_success_rate_difference'],-1)
