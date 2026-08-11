import pytest
from signaling.report_generator import ReportGenerator
from signaling.signaler import Signaler
from models.signaling import (SignalingCategory, SeverityLevel)
from tests.fixtures import (sinalizador_vazio, sinalizador_com_tres_niveis)


def test_montar_texto_com_lista_vazia_retorna_mensagem_padrao():
    generator = ReportGenerator()

    text = generator._build_text([])

    assert "Nenhum ponto sinalizado nesta conversão." in text

def test_montar_texto_agrupa_por_nivel_na_ordem_correta():
    generator = ReportGenerator()
    signaler = sinalizador_com_tres_niveis()

    text = generator._build_text(signaler.ordered_report())

    decision_index = text.index("REQUER DECISÃO")
    verify_index = text.index("VERIFICAR")
    informational_index = text.index("INFORMATIVO")
    assert decision_index < verify_index < informational_index

def test_montar_texto_conta_itens_por_secao_corretamente():
    generator = ReportGenerator()
    signaler = Signaler()
    signaler.register(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "a", 1)
    signaler.register(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "b", 2)
    signaler.register(SignalingCategory.AMBIGUOUS_KEY, SeverityLevel.VERIFY, "c", 3)

    text = generator._build_text(signaler.ordered_report())

    assert "REQUER DECISÃO (2)" in text
    assert "VERIFICAR (1)" in text
    assert "INFORMATIVO" not in text

def test_formatar_linha_inclui_compasso_e_descricao():
    generator = ReportGenerator()
    signaler = Signaler()
    signaler.register(SignalingCategory.IMPOSSIBLE_PASSAGE, SeverityLevel.REQUIRES_DECISION, "descrição de teste", 7)

    line = generator._format_line(signaler.all()[0])

    assert line == "Compasso 7: descrição de teste"

def test_gerar_cria_arquivo_mesmo_sem_sinalizacoes(tmp_path):
    generator = ReportGenerator()
    signaler = sinalizador_vazio()
    path = tmp_path / "relatorio.txt"

    generator.generate(signaler, str(path))

    assert path.exists()
    assert "Nenhum ponto sinalizado" in path.read_text(encoding="utf-8")

def test_gerar_cria_diretorio_de_destino_se_nao_existir(tmp_path):
    generator = ReportGenerator()
    signaler = sinalizador_vazio()
    path = tmp_path / "subpasta" / "relatorio.txt"

    generator.generate(signaler, str(path))

    assert path.exists()