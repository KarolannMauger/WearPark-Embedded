# Tests WearPark

## Structure Simple

```
tests/
└── unit/          # Tests unitaires  
```

## Installation

```bash
pip install -r requirements-test.txt
```

## Commandes Rapides (Makefile)

```bash
make test       # Lance pytest avec coverage
make security   # Lance bandit + pip-audit  
make clean      # Nettoie les fichiers temporaires
```

## Tests Unitaires

```bash
# Lancer tous les tests
pytest

# Juste les tests unitaires
pytest src/tests/unit/

# Avec détails
pytest -v

# Coverage HTML
pytest --cov=wearpark --cov-report=html
# Ouvrir: htmlcov/index.html
```

## Sécurité

```bash
# Scan du code
bandit -r src/wearpark/

# Scan des dépendances
pip-audit
```

C'est tout! 🚀
