.PHONY: up down backend seed demo-pre-live-check demo-stream-down demo-stream-recover demo-no-audio demo-segment-stalled demo-coupon demo-inventory demo-price demo-price-risk demo-post-live-report eval test

PYTHON ?= $(CURDIR)/meerkat_backend/.venv/bin/python

up:
	docker compose up -d owncast

backend:
	cd meerkat_backend && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8018 --reload

seed:
	cd meerkat_backend && $(PYTHON) -m app.db.init_db --reset && $(PYTHON) -m app.db.seed

demo-coupon:
	$(PYTHON) scripts/run_demo_coupon.py

demo-pre-live-check:
	$(PYTHON) scripts/run_demo_pre_live_check.py

demo-inventory:
	$(PYTHON) scripts/run_demo_inventory.py

demo-price:
	$(PYTHON) scripts/run_demo_price.py

demo-price-risk:
	$(PYTHON) scripts/run_demo_price.py

demo-stream-down:
	$(PYTHON) scripts/run_demo_stream_down.py

demo-stream-recover:
	$(PYTHON) scripts/run_demo_stream_recover.py

demo-no-audio:
	$(PYTHON) scripts/run_demo_no_audio.py

demo-segment-stalled:
	$(PYTHON) scripts/run_demo_segment_stalled.py

demo-post-live-report:
	$(PYTHON) scripts/run_demo_post_live_report.py

eval:
	cd meerkat_agent/evals && $(PYTHON) run_eval.py

test:
	cd meerkat_backend && $(PYTHON) -m pytest -q

down:
	docker compose down
