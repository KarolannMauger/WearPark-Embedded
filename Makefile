.PHONY: test security clean help

help:
	@echo "WearPark-Embedded - Commandes disponibles:"
	@echo ""
	@echo "  make test      - Lance tous les tests (pytest)"
	@echo "  make security  - Scan de sécurité (bandit + pip-audit)"
	@echo "  make clean     - Nettoie les fichiers temporaires"
	@echo ""

test:
	pytest

security:
	@echo "Scan du code..."
	bandit -r src/wearpark/
	@echo ""
	@echo "Scan des dépendances..."
	pip-audit

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov reports 2>/dev/null || true
	@echo "Nettoyage terminé"
