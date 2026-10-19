.PHONY: help install test test-p1 test-p2 test-p3 rtm triage demo clean

VENV = .venv
PYTHON = $(VENV)/bin/python
PYTEST = $(VENV)/bin/pytest

help:
	@echo "Portefeuille QA Système & Médical - Dispositif Médical"
	@echo "----------------------------------------------------"
	@echo "make install    : Installe les dépendances dans .venv"
	@echo "make test       : Exécute tous les tests PyTest (P1, P2, P3)"
	@echo "make rtm        : Génère la matrice de traçabilité IEC 62304"
	@echo "make triage     : Lance le diagnostic multi-logs et génère le ticket"
	@echo "make demo       : Exécute la démonstration complète de la plateforme"

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

test:
	PYTHONPATH=. $(PYTEST) -v

test-p1:
	PYTHONPATH=. $(PYTEST) project_1_fw_testbench/tests/ -v

test-p2:
	PYTHONPATH=. $(PYTEST) project_2_iec62304_bdd/step_defs/ -v

test-p3:
	PYTHONPATH=. $(PYTEST) project_3_log_correlator/tests/ -v

rtm:
	PYTHONPATH=. $(PYTHON) project_2_iec62304_bdd/tools/generate_rtm.py

triage:
	PYTHONPATH=. $(PYTHON) project_3_log_correlator/log_triage.py

demo:
	PYTHONPATH=. $(PYTHON) run_all_demos.py

clean:
	rm -rf __pycache__ .pytest_cache docs/RTM_Report.md docs/Defect_Report_TargetProcess.md
