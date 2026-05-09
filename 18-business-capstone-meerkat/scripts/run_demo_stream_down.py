from _demo_common import stream_main

stream_main(
    "stream-down",
    "stream_down",
    [
        {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
        {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
        {"is_live": False, "probe_status": "FAILED", "probe_error": "HLS playlist unavailable"},
    ],
)
