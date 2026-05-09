# Meerkat V1 Status

Last acceptance run:
  date: 2026-05-09T16:08:52Z
  git commit: ccf3139
  command: make acceptance-v1
  result: PASS
  passed checks:
    - backend health
    - owncast health
    - owncast webhook
    - coupon flow
    - price approval
    - probe loop
    - trace replay
    - dashboard summary
    - eval metrics
  failed checks: []
  skipped checks: []
  trace ids:
    - tr_20260510000850_abee9d
    - tr_20260510000850_5ee307
    - tr_20260510000850_d3c7cf
  eval metrics:
    alert_type_accuracy: 1.00
    subagent_dispatch_coverage: 1.00
    tool_selection_accuracy: 1.00
    tool_call_recall: 1.00
    tool_call_precision: 1.00
    tool_execution_success_rate: 1.00
    forbidden_tool_block_rate: 1.00
    risk_gate_accuracy: 1.00
    approval_trigger_accuracy: 1.00
    policy_grounding_accuracy: 1.00
    speaker_note_created_rate: 1.00
    trace_completeness: 1.00
    p95_end_to_end_latency: 35.00
  owncast runtime:
    service: running on http://127.0.0.1:8080
    webhook: configured for http://host.docker.internal:8018/api/v1/integrations/owncast/webhook
    stream: online after `make ffmpeg-stream-docker`; offline means no RTMP source is currently pushing
    real chat: verified through Owncast UI; latest comment persisted with `owncast_event_id`
  known gaps: none from acceptance/eval
