import sys
from pathlib import Path
import unittest
import json
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_clean_baseline import summarize, validate_report, collect_rows

class BaselineSummaryTest(unittest.TestCase):
    def test_technical_errors_are_not_task_failures(self):
        result=summarize([
            {'status':'completed','success':True,'technical_error_attempts':0},
            {'status':'completed','success':False,'technical_error_attempts':0},
            {'status':'pending','success':'','technical_error_attempts':1}])
        self.assertEqual(result['completed'],2)
        self.assertEqual(result['success_rate'],0.5)
        self.assertEqual(result['task_failures'],1)
        self.assertEqual(result['pending'],1)
        self.assertEqual(result['technical_error_attempts'],1)

    def test_incompatible_episode_cannot_be_reused(self):
        settings={'task_id':0,'seed':0,'steps':220,'policy':{'revision':'a'}}
        report={'task_id':0,'seed':0,'requested_steps':220,'condition':'clean',
                'initial_state_id':1,'policy':{'revision':'b'}}
        with self.assertRaises(ValueError):
            validate_report(report,settings,1)

    def test_incomplete_rollout_is_not_a_completed_failure(self):
        settings={'task_id':0,'seed':0,'steps':220,'policy':{}}
        report={'task_id':0,'seed':0,'requested_steps':220,'condition':'clean',
                'initial_state_id':1,'policy':{},'termination':'step_limit','completed_steps':10}
        with self.assertRaises(ValueError):
            validate_report(report,settings,1)

    def test_log_files_do_not_count_as_episode_attempts(self):
        settings={'task_id':0,'seed':0,'steps':220,'policy':{},'initial_state_ids':[0]}
        report={'task_id':0,'seed':0,'requested_steps':220,'condition':'clean',
                'initial_state_id':0,'policy':{},'termination':'success','success':True,
                'completed_steps':80,'latencies_seconds':[1.5]}
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            attempt=out/'state-00/attempt-01'; attempt.mkdir(parents=True)
            (attempt/'report.json').write_text(json.dumps(report))
            (attempt.parent/'attempt-01.log').write_text('episode log')
            rows=collect_rows(out,settings)
            self.assertEqual(rows[0]['attempts'],1)
            self.assertEqual(rows[0]['technical_error_attempts'],0)

    def test_disturbance_settings_must_match_exactly(self):
        settings={'task_id':0,'seed':0,'steps':220,'policy':{},'condition':'brightness_shift',
                  'disturbance':{'name':'brightness_shift','factor':.35}}
        report={'task_id':0,'seed':0,'requested_steps':220,'initial_state_id':0,'policy':{},
                'condition':'brightness_shift','disturbance':{'name':'brightness_shift','factor':.5}}
        with self.assertRaises(ValueError):
            validate_report(report,settings,0)
