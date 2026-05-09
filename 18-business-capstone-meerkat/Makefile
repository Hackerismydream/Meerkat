.PHONY: up down backend seed demo-coupon demo-inventory demo-price eval test

up:
	docker compose up -d owncast

backend:
	cd meerkat_backend && uvicorn app.main:app --host 0.0.0.0 --port 8018 --reload

seed:
	cd meerkat_backend && python -m app.db.init_db && python -m app.db.seed

demo-coupon:
	python scripts/run_demo_coupon.py

demo-inventory:
	python scripts/run_demo_inventory.py

demo-price:
	python scripts/run_demo_price.py

eval:
	cd meerkat_agent/evals && python run_eval.py

test:
	cd meerkat_backend && pytest -q

down:
	docker compose down
