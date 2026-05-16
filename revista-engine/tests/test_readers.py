"""
Testes da camada de readers.

Cria fixtures temporárias que reproduzem as duas convenções reais que vi no Drive:
- Gardens Living 04/2026: convenção plana (fotos soltas + .txt cujo nome é descrição)
- Villa Park Osasco 04/2026: convenção com subpastas por manutenção

Roda com: python3 tests/test_readers.py
"""

import sys
import tempfile
from pathlib import Path

# Permitir import do pacote engine sem instalar
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.models import BadgeKind, infer_badge
from engine.readers import FlatFolderReader, SubFoldersReader, detect_convention, read_groups


# ANSI colors para output
G = "\033[92m"  # green
R = "\033[91m"  # red
Y = "\033[93m"  # yellow
B = "\033[94m"  # blue
RESET = "\033[0m"

passed = 0
failed = 0


def assert_eq(actual, expected, label):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  {G}✓{RESET} {label}")
    else:
        failed += 1
        print(f"  {R}✗{RESET} {label}")
        print(f"      esperado: {expected!r}")
        print(f"      obtido:   {actual!r}")


def assert_true(cond, label):
    global passed, failed
    if cond:
        passed += 1
        print(f"  {G}✓{RESET} {label}")
    else:
        failed += 1
        print(f"  {R}✗{RESET} {label}")


def section(title):
    print(f"\n{B}━━━ {title} ━━━{RESET}")


# ============================================================================
# Suite 1 — infer_badge (lógica de inferência por palavras-chave)
# ============================================================================

def test_infer_badge():
    section("infer_badge — inferência de badge por palavras-chave")

    # Casos da Villa Park 04/2026 (nomes reais)
    assert_eq(infer_badge("Manutenção Jardim"), BadgeKind.JARDIM, "Manutenção Jardim → JARDIM")
    assert_eq(infer_badge("Iluminação da Cancela"), BadgeKind.SEGURANCA, "Iluminação da Cancela → SEGURANÇA (cancela)")
    assert_eq(infer_badge("Reparo motor de saída veicular"), BadgeKind.MANUTENCAO, "Reparo motor → MANUTENÇÃO")
    assert_eq(infer_badge("Solda do Portão"), BadgeKind.SEGURANCA, "Solda do Portão → SEGURANÇA (portão)")
    assert_eq(infer_badge("Manutenção Preventiva de Bombas"), BadgeKind.MANUTENCAO, "Bombas → MANUTENÇÃO")
    assert_eq(infer_badge("Substituição da Esteira da Academia"), BadgeKind.MANUTENCAO, "Substituição esteira → MANUTENÇÃO")
    assert_eq(infer_badge("Troca iluminação de jardim"), BadgeKind.JARDIM, "Troca iluminação de JARDIM (jardim ganha)")
    assert_eq(infer_badge("Dedetização e desratização"), BadgeKind.MANUTENCAO, "Dedetização → MANUTENÇÃO")

    # Casos da Gardens 04/2026 (nomes de .txt como descrição)
    assert_eq(
        infer_badge("Nova restauração da grama ao lado do banheiro e cozinha"),
        BadgeKind.JARDIM,
        "grama → JARDIM",
    )
    assert_eq(
        infer_badge("Árvore novo no condomínio. Por conta da queda da árvore..."),
        BadgeKind.JARDIM,
        "árvore → JARDIM",
    )

    # Engenharia / fachada
    assert_eq(infer_badge("Vistoria Técnica de Fachada"), BadgeKind.ENGENHARIA, "Fachada/Vistoria → ENGENHARIA")
    assert_eq(infer_badge("Visita da Engenharia (Fachada)"), BadgeKind.ENGENHARIA, "Engenharia → ENGENHARIA")

    # Override manual via [tag]
    assert_eq(
        infer_badge("Pintura do Hall Social [engenharia]"),
        BadgeKind.ENGENHARIA,
        "Override [engenharia] vence",
    )
    assert_eq(
        infer_badge("Manutenção Geral [jardim]"),
        BadgeKind.JARDIM,
        "Override [jardim] vence sobre 'manutenção'",
    )

    # Default
    assert_eq(infer_badge("Algo Novo"), BadgeKind.MANUTENCAO, "Sem palavras-chave → MANUTENÇÃO (default)")


# ============================================================================
# Suite 2 — SubFoldersReader (Villa Park style)
# ============================================================================

def test_sub_folders_reader_villa_park_simulado():
    section("SubFoldersReader — simulando Villa Park 04/2026")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Villa Park Osasco"
        root.mkdir()

        # Reproduzindo subpastas reais que vi no Drive (Villa Park 04/2026)
        manutencoes = {
            "Manutenção Jardim": 8,                          # virá hero (6+)
            "Substituição da Esteira da Academia": 4,        # large (3-5)
            "Iluminação da Cancela": 2,                      # small (1-2)
            "Manutenção Preventiva de Bombas": 5,            # large
            "Solda do Portão": 1,                            # small
            "Reparo de Tubulação": 3,                        # large
            "Dedetização e desratização": 7,                 # hero
        }

        for name, n_photos in manutencoes.items():
            subf = root / name
            subf.mkdir()
            for i in range(n_photos):
                (subf / f"foto-{i+1}.jpg").write_bytes(b"fake-jpeg-content" * 1000)

        # Arquivo de descrição numa subpasta (opcional)
        (root / "Manutenção Jardim" / "descricao.txt").write_text(
            "Realizamos a poda completa de todas as árvores do bloco A, "
            "removendo galhos secos e fazendo a adubação do solo.",
            encoding="utf-8",
        )

        # Subpasta vazia (deve ser ignorada com aviso)
        (root / "Pasta Vazia").mkdir()

        # Subpasta de sistema (deve ser ignorada)
        (root / "_OUTPUT").mkdir()
        (root / "_OUTPUT" / "Revista_Final.pdf").write_bytes(b"pdf")

        # Rodar reader
        reader = SubFoldersReader(root)
        groups = reader.read()

        # Asserts
        assert_eq(len(groups), 7, "7 manutenções com fotos detectadas (vazia ignorada)")

        # Encontrar grupo de Jardim e validar
        jardim = next((g for g in groups if "Jardim" in g.title), None)
        assert_true(jardim is not None, "Grupo 'Manutenção Jardim' encontrado")
        assert_eq(jardim.badge, BadgeKind.JARDIM, "Badge JARDIM inferido")
        assert_eq(jardim.num_photos, 8, "8 fotos no grupo Jardim")
        assert_eq(jardim.display_size, "hero", "Display 'hero' (6+ fotos)")
        assert_true(len(jardim.description) > 30, "Descrição do .txt foi lida")

        # Validar regras de display_size em diferentes tamanhos
        cancela = next(g for g in groups if "Cancela" in g.title)
        assert_eq(cancela.display_size, "small", "Iluminação da Cancela com 2 fotos → small")

        bombas = next(g for g in groups if "Bombas" in g.title)
        assert_eq(bombas.display_size, "large", "Bombas com 5 fotos → large")

        dedetizacao = next(g for g in groups if "Dedetização" in g.title)
        assert_eq(dedetizacao.display_size, "hero", "Dedetização com 7 fotos → hero")


# ============================================================================
# Suite 3 — FlatFolderReader (Gardens style)
# ============================================================================

def test_flat_folder_reader_gardens_simulado():
    section("FlatFolderReader — simulando Gardens 04/2026")

    import os
    import time

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "Gardens Living"
        root.mkdir()

        # Reproduzindo a estrutura plana real:
        # - Fotos PHOTO-YYYY-MM-DD-HH-MM-SS.jpg
        # - Arquivos .txt cujo nome é a descrição

        # Grupo 1 — Restauração de grama (fotos por volta de 2026-03-30)
        for i, ts in enumerate([
            "PHOTO-2026-03-30-11-22-56.jpg",
            "PHOTO-2026-03-30-11-23-12.jpg",
            "PHOTO-2026-03-30-13-22-07.jpg",
            "PHOTO-2026-03-30-13-22-13.jpg",
        ]):
            (root / ts).write_bytes(b"jpeg-fake" * 500)

        # .txt-descrição (mtime ajustado para coincidir)
        txt1 = root / "Nova restauração da grama ao lado do banheiro e cozinha.txt"
        txt1.write_text("Realizada em 30/03/2026.", encoding="utf-8")
        # Ajustar mtime do txt para 2026-03-30 13:00 UTC
        ts_target = time.mktime((2026, 3, 30, 13, 0, 0, 0, 0, 0))
        os.utime(txt1, (ts_target, ts_target))
        # E ajustar mtime das fotos também (para o teste ser determinístico)
        for f in [
            "PHOTO-2026-03-30-11-22-56.jpg",
            "PHOTO-2026-03-30-11-23-12.jpg",
            "PHOTO-2026-03-30-13-22-07.jpg",
            "PHOTO-2026-03-30-13-22-13.jpg",
        ]:
            ts_f = time.mktime((2026, 3, 30, 13, 0, 0, 0, 0, 0))
            os.utime(root / f, (ts_f, ts_f))

        # Grupo 2 — Árvore nova (timestamp diferente)
        (root / "PHOTO-2026-03-10-09-02-50.jpg").write_bytes(b"jpeg-fake" * 500)
        (root / "PHOTO-2026-03-10-09-02-58.jpg").write_bytes(b"jpeg-fake" * 500)
        ts_2 = time.mktime((2026, 3, 10, 9, 0, 0, 0, 0, 0))
        for f in ["PHOTO-2026-03-10-09-02-50.jpg", "PHOTO-2026-03-10-09-02-58.jpg"]:
            os.utime(root / f, (ts_2, ts_2))

        txt2 = root / "Árvore novo no condomínio plantada após queda da anterior.txt"
        txt2.write_text("Replantio.", encoding="utf-8")
        os.utime(txt2, (ts_2, ts_2))

        # Foto órfã (fora da janela de qualquer txt)
        orfa = root / "PHOTO-2026-03-01-08-00-00.jpg"
        orfa.write_bytes(b"jpeg-fake" * 500)
        ts_orfa = time.mktime((2026, 3, 1, 8, 0, 0, 0, 0, 0))
        os.utime(orfa, (ts_orfa, ts_orfa))

        # Lixo que deve ser ignorado
        (root / ".DS_Store").write_bytes(b"binary")
        (root / "ok.txt").write_text("nada")  # nome curto, não é descrição

        # Rodar reader
        reader = FlatFolderReader(root)
        groups = reader.read()

        # Validar: 2 grupos com fotos + 1 órfão = 3 grupos
        assert_eq(len(groups), 3, "3 grupos detectados (2 com texto + 1 de órfãs)")

        grama = next((g for g in groups if "grama" in g.title.lower()), None)
        assert_true(grama is not None, "Grupo de restauração de grama encontrado")
        assert_eq(grama.badge, BadgeKind.JARDIM, "Badge JARDIM inferido (palavra 'grama')")
        assert_eq(grama.num_photos, 4, "4 fotos agrupadas pelo timestamp 30/03")

        arvore = next((g for g in groups if "rvore" in g.title.lower()), None)
        assert_true(arvore is not None, "Grupo de árvore encontrado")
        assert_eq(arvore.badge, BadgeKind.JARDIM, "Badge JARDIM (palavra 'arvore')")
        assert_eq(arvore.num_photos, 2, "2 fotos do replantio")

        orfas = next((g for g in groups if "Outros" in g.title), None)
        assert_true(orfas is not None, "Grupo 'Outros Registros' criado para foto órfã")
        assert_eq(orfas.num_photos, 1, "1 foto órfã capturada")


# ============================================================================
# Suite 4 — auto_detect e read_groups
# ============================================================================

def test_auto_detect():
    section("auto_detect — detecção da convenção em uso")

    with tempfile.TemporaryDirectory() as tmp:
        # Caso A — Convenção subfolders (simulando Villa Park)
        a = Path(tmp) / "case_a"
        a.mkdir()
        for n in ["Manutenção 1", "Manutenção 2", "Manutenção 3", "Manutenção 4"]:
            sub = a / n
            sub.mkdir()
            (sub / "foto.jpg").write_bytes(b"jpg")
        assert_eq(detect_convention(a), "subfolders", "4 subpastas com foto → subfolders")

        # Caso B — Convenção plana (simulando Gardens)
        b = Path(tmp) / "case_b"
        b.mkdir()
        for i in range(4):
            (b / f"PHOTO-2026-03-{10+i:02d}-12-00-00.jpg").write_bytes(b"jpg")
        for nome in [
            "Pintura do hall principal realizada em março.txt",
            "Troca da bomba dágua central no subsolo.txt",
            "Vistoria técnica anual da cobertura realizada.txt",
        ]:
            (b / nome).write_text("desc", encoding="utf-8")
        assert_eq(detect_convention(b), "flat", "Fotos soltas + 3 .txt-descrição → flat")

        # Caso C — Misto (raro mas possível)
        c = Path(tmp) / "case_c"
        c.mkdir()
        for n in ["Sub 1", "Sub 2", "Sub 3"]:
            (c / n).mkdir()
            (c / n / "foto.jpg").write_bytes(b"jpg")
        for nome in [
            "Ajuste manual feito no portão da garagem.txt",
            "Limpeza pesada do salão após evento.txt",
            "Reparo emergencial do elevador social.txt",
        ]:
            (c / nome).write_text("desc", encoding="utf-8")
        assert_eq(detect_convention(c), "mixed", "Subpastas + .txt-descrição → mixed")

        # Caso D — Pasta quase vazia (default flat)
        d = Path(tmp) / "case_d"
        d.mkdir()
        (d / "foto.jpg").write_bytes(b"jpg")
        assert_eq(detect_convention(d), "flat", "Pasta esparsa → flat (default tolerante)")


def test_read_groups_integration():
    section("read_groups — pipeline completo")

    with tempfile.TemporaryDirectory() as tmp:
        # Pasta no estilo Villa Park
        root = Path(tmp) / "vila"
        root.mkdir()
        for n in ["Manutenção Jardim", "Solda do Portão", "Reparo Tubulação"]:
            sub = root / n
            sub.mkdir()
            for i in range(3):
                (sub / f"f{i}.jpg").write_bytes(b"jpg" * 100)

        groups, conv = read_groups(root)

        assert_eq(conv, "subfolders", "Detectou convenção subfolders")
        assert_eq(len(groups), 3, "3 grupos lidos")

        jardim = next(g for g in groups if "Jardim" in g.title)
        assert_eq(jardim.badge, BadgeKind.JARDIM, "Badge inferido corretamente")
        assert_eq(jardim.display_size, "large", "3 fotos = large")


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    print(f"\n{B}═══ revista-engine: testes da camada de readers ═══{RESET}")

    test_infer_badge()
    test_sub_folders_reader_villa_park_simulado()
    test_flat_folder_reader_gardens_simulado()
    test_auto_detect()
    test_read_groups_integration()

    print(f"\n{B}═══ Resultado ═══{RESET}")
    print(f"  {G}{passed} passed{RESET}, {R}{failed} failed{RESET}")

    sys.exit(0 if failed == 0 else 1)
