"""Importa prospects de um CSV para o LeadDesk.

Cadastrar 30 empresas uma a uma pela API não é trabalho de gente. Este script
lê um CSV, valida cada linha contra os enums do módulo e grava em lote.

Uso:
    python scripts/import_prospects.py lista.csv --dry-run
    python scripts/import_prospects.py lista.csv
    python scripts/import_prospects.py lista.csv --week 2026-08-03

Colunas obrigatórias:
    company_name

Colunas opcionais, ignoradas quando ausentes ou vazias:
    segment, source, size_estimate, contact_name, phone, email,
    linkedin_url, signals, notes, week

Qualquer outra coluna é ignorada em silêncio — assim o CSV pode carregar
campos de trabalho (endereço, link do OSM, coordenadas) sem atrapalhar.

Empresa que já existe no banco é pulada, não duplicada: a comparação é pelo
nome, sem diferenciar maiúscula de minúscula.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from crm.database import Base, SessionLocal, engine  # noqa: E402
from prospecting.models import Prospect, ProspectSource, ProspectStatus, Segment  # noqa: E402

CAMPOS_TEXTO = (
    "size_estimate",
    "contact_name",
    "phone",
    "email",
    "linkedin_url",
    "signals",
    "notes",
)


@dataclass
class Resultado:
    importados: list[str] = field(default_factory=list)
    repetidos: list[str] = field(default_factory=list)
    ignorados: list[tuple[int, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.importados) + len(self.repetidos) + len(self.ignorados)


def segunda_da_semana(referencia: date | None = None) -> date:
    hoje = referencia or date.today()
    return hoje - timedelta(days=hoje.weekday())


def _enum_ou_padrao(bruto: str, enum, padrao):
    valor = (bruto or "").strip().lower()
    try:
        return enum(valor)
    except ValueError:
        return padrao


def importar(
    db: Session,
    linhas: list[dict[str, str]],
    semana: date | None = None,
    dry_run: bool = False,
) -> Resultado:
    semana = semana or segunda_da_semana()
    resultado = Resultado()

    existentes = {
        nome.casefold() for (nome,) in db.execute(select(Prospect.company_name)).all()
    }

    for numero, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        nome = (linha.get("company_name") or "").strip()
        if not nome:
            resultado.ignorados.append((numero, "sem company_name"))
            continue

        chave = nome.casefold()
        if chave in existentes:
            resultado.repetidos.append(nome)
            continue
        existentes.add(chave)

        dados = {
            "company_name": nome,
            "segment": _enum_ou_padrao(linha.get("segment", ""), Segment, Segment.outro),
            "source": _enum_ou_padrao(
                linha.get("source", ""), ProspectSource, ProspectSource.google_maps
            ),
            "status": ProspectStatus.pesquisando,
            "week": semana,
        }
        for campo in CAMPOS_TEXTO:
            valor = (linha.get(campo) or "").strip()
            if valor:
                dados[campo] = valor

        semana_da_linha = (linha.get("week") or "").strip()
        if semana_da_linha:
            try:
                dados["week"] = segunda_da_semana(date.fromisoformat(semana_da_linha))
            except ValueError:
                resultado.ignorados.append((numero, f"week invalida: {semana_da_linha}"))
                continue

        if not dry_run:
            db.add(Prospect(**dados))
        resultado.importados.append(nome)

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return resultado


def ler_csv(caminho: Path) -> list[dict[str, str]]:
    with caminho.open(newline="", encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    if linhas and "company_name" not in linhas[0]:
        raise SystemExit("CSV sem a coluna obrigatória company_name.")
    return linhas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument(
        "--dry-run", action="store_true", help="mostra o que faria sem gravar nada"
    )
    parser.add_argument("--week", help="segunda-feira da semana de prospecção (AAAA-MM-DD)")
    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"Arquivo não encontrado: {args.csv}")

    semana = segunda_da_semana(date.fromisoformat(args.week)) if args.week else None

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        resultado = importar(db, ler_csv(args.csv), semana=semana, dry_run=args.dry_run)
    finally:
        db.close()

    prefixo = "[simulação] " if args.dry_run else ""
    print(f"\n{prefixo}{args.csv}  —  {resultado.total} linhas")
    print(f"  {len(resultado.importados)} importados")
    print(f"  {len(resultado.repetidos)} já existiam, pulados")
    print(f"  {len(resultado.ignorados)} ignorados")
    for numero, motivo in resultado.ignorados:
        print(f"    linha {numero}: {motivo}")
    if args.dry_run:
        print("\nNada foi gravado. Rode sem --dry-run para importar.")


if __name__ == "__main__":
    main()
