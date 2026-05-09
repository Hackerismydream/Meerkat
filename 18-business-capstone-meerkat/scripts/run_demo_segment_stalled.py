from _demo_common import stream_main

stream_main(
    "segment-stalled",
    "segment_stalled",
    [{"is_live": True, "last_segment_age_ms": 15000, "probe_status": "OK"}],
)
