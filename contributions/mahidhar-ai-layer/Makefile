.PHONY: help install data tune prompts test demo all clean

help:
	@echo "make install   install dependencies"
	@echo "make data      regenerate the sample lead dataset"
	@echo "make tune      Day 14: tune scoring weights (+ report)"
	@echo "make prompts   Day 14: compare prompt variants (structural)"
	@echo "make test      run the full test suite"
	@echo "make demo      run the headless demo of all three AI services"
	@echo "make all       data + tune + test (everything a reviewer needs)"

install:
	pip install -r requirements.txt

data:
	python scripts/generate_sample_data.py

tune:
	python scripts/tune_weights.py --seed 42

prompts:
	python scripts/tune_prompts.py

test:
	python -m pytest

demo:
	python scripts/run_ai_demo.py

all: data tune test
	@echo "Artifacts in data/artifacts/ — open the tuning report for the review."
