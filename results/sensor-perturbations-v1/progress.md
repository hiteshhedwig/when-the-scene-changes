# Sensor-input pilot progress

Status: **complete**. **20/20** planned disturbed episodes completed. Technical interruptions are preserved and are not model task failures.

| Condition | Completed | Successful completed trials | Pending |
| --- | ---: | ---: | ---: |
| brightness_shift | 10/10 | 9/10 | 0 |
| camera_occlusion | 10/10 | 0/10 | 0 |

| Condition | State | Clean actions | Disturbed outcome / actions | Model-input video |
| --- | ---: | ---: | --- | --- |
| brightness_shift | 0 | 76 | Success / 76 | [Watch](brightness_shift/state-00/attempt-01/policy-input.mp4) |
| brightness_shift | 1 | 78 | Success / 80 | [Watch](brightness_shift/state-01/attempt-01/policy-input.mp4) |
| brightness_shift | 2 | 85 | Step limit / 220 | [Watch](brightness_shift/state-02/attempt-02/policy-input.mp4) |
| brightness_shift | 3 | 74 | Success / 83 | [Watch](brightness_shift/state-03/attempt-01/policy-input.mp4) |
| brightness_shift | 4 | 76 | Success / 74 | [Watch](brightness_shift/state-04/attempt-01/policy-input.mp4) |
| brightness_shift | 5 | 74 | Success / 72 | [Watch](brightness_shift/state-05/attempt-01/policy-input.mp4) |
| brightness_shift | 6 | 73 | Success / 75 | [Watch](brightness_shift/state-06/attempt-01/policy-input.mp4) |
| brightness_shift | 7 | 82 | Success / 81 | [Watch](brightness_shift/state-07/attempt-01/policy-input.mp4) |
| brightness_shift | 8 | 86 | Success / 81 | [Watch](brightness_shift/state-08/attempt-01/policy-input.mp4) |
| brightness_shift | 9 | 78 | Success / 82 | [Watch](brightness_shift/state-09/attempt-01/policy-input.mp4) |
| camera_occlusion | 0 | 76 | Step limit / 220 | [Watch](camera_occlusion/state-00/attempt-01/policy-input.mp4) |
| camera_occlusion | 1 | 78 | Step limit / 220 | [Watch](camera_occlusion/state-01/attempt-01/policy-input.mp4) |
| camera_occlusion | 2 | 85 | Step limit / 220 | [Watch](camera_occlusion/state-02/attempt-01/policy-input.mp4) |
| camera_occlusion | 3 | 74 | Step limit / 220 | [Watch](camera_occlusion/state-03/attempt-01/policy-input.mp4) |
| camera_occlusion | 4 | 76 | Step limit / 220 | [Watch](camera_occlusion/state-04/attempt-01/policy-input.mp4) |
| camera_occlusion | 5 | 74 | Step limit / 220 | [Watch](camera_occlusion/state-05/attempt-01/policy-input.mp4) |
| camera_occlusion | 6 | 73 | Step limit / 220 | [Watch](camera_occlusion/state-06/attempt-01/policy-input.mp4) |
| camera_occlusion | 7 | 82 | Step limit / 220 | [Watch](camera_occlusion/state-07/attempt-01/policy-input.mp4) |
| camera_occlusion | 8 | 86 | Step limit / 220 | [Watch](camera_occlusion/state-08/attempt-01/policy-input.mp4) |
| camera_occlusion | 9 | 78 | Step limit / 220 | [Watch](camera_occlusion/state-09/attempt-01/policy-input.mp4) |

## Technical interruptions

- brightness_shift, state 2: 69 completed actions before HTTPError: HTTP Error 502: Bad Gateway. [Preserved attempt](brightness_shift/state-02/attempt-01/report.json).

Protocol: darken RGB pixels to 35% intensity, or mask a fixed 96×96 rectangle, at zero-based policy steps 30–59. Normal input returns at 60. No recovery is enabled. These are camera-input corruptions, not physical lighting or object movement.

Partial success counts do not estimate the final ten-state condition result. Severity/timing remain frozen. All videos omit network waiting; raw simulator videos are saved beside model-input videos.

[Frozen protocol](protocol.json) · [Paired outcome progress](comparison.json) · [Artifact validation](artifact-validation.json)
