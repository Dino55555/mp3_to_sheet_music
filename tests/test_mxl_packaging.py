import zipfile
from mxl_packaging import package_mxl


def test_empacotar_mxl_produz_zip_com_container_xml(tmp_path):
    musicxml_path = tmp_path / "peca.musicxml"
    musicxml_path.write_text("<score-partwise></score-partwise>", encoding="utf-8")
    mxl_path = tmp_path / "peca.mxl"

    package_mxl(str(musicxml_path), str(mxl_path))

    with zipfile.ZipFile(str(mxl_path), 'r') as zip_file:
        names = zip_file.namelist()
        assert "META-INF/container.xml" in names
        assert "peca.musicxml" in names

def test_empacotar_mxl_conteudo_musicxml_e_identico_ao_arquivo_original(tmp_path):
    musicxml_path = tmp_path / "peca.musicxml"
    original_content = "<score-partwise>conteudo de teste com acentuação e tudo</score-partwise>"
    musicxml_path.write_text(original_content, encoding="utf-8")
    mxl_path = tmp_path / "peca.mxl"

    package_mxl(str(musicxml_path), str(mxl_path))

    with zipfile.ZipFile(str(mxl_path), 'r') as zip_file:
        packaged_content = zip_file.read("peca.musicxml").decode("utf-8")

    assert packaged_content == original_content