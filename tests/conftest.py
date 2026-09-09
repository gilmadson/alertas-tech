import sys
from pathlib import Path

# `scripts/` não é pacote instalável — a landing é um site estático com um
# utilitário ao lado. Entrar no sys.path aqui evita ter que empacotar isso.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
