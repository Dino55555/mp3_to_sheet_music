from __future__ import annotations
import os
import zipfile

_CONTAINER_XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="{filename}"/>
  </rootfiles>
</container>
'''


def package_mxl(musicxml_path: str, mxl_path: str) -> None:
    #Deriva o .mxl do .musicxml ja escrito em disco - nunca gera o
    #conteudo de novo, evitando duas chamadas independentes ao motor de
    #exportacao precisarem concordar entre si
    musicxml_filename = os.path.basename(musicxml_path)

    with open(musicxml_path, 'rb') as file:
        musicxml_content = file.read()

    container_content = _CONTAINER_XML_TEMPLATE.format(filename=musicxml_filename)

    with zipfile.ZipFile(mxl_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('META-INF/container.xml', container_content)
        zip_file.writestr(musicxml_filename, musicxml_content)