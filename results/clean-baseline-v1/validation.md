# Validation record

- All ten episode reports indicate task success and normal success termination.
- Every action trace has exactly the reported number of steps and ends with the success predicate true.
- Each episode has a nonempty saved video; the batch manifest is complete.
- The final table counts each initial state once and records exactly one episode attempt per state. State 0 was imported from the earlier exploratory successful run.
- Four baseline aggregation/resume validation tests and three prompt-mask regression tests passed on the final rerun.
- Five HTTP protocol tests passed earlier, along with a real mock-policy LIBERO integration episode and the actual cloud-policy episodes. Their final rerun was blocked by the execution sandbox denying creation of a socket (PermissionError); this was not a robot episode failure.
- The generated chart was visually inspected. No brightness, occlusion, or object-displacement experiment is included in this clean pilot.
