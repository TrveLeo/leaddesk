"""Servir a interface: o mount estático não pode sombrear a API."""

from main import STATIC_DIR


def test_a_raiz_avisa_quando_a_interface_ainda_nao_existe(client):
    if (STATIC_DIR / "index.html").is_file():
        return  # interface já construída — coberto pelo teste abaixo

    r = client.get("/")

    assert r.status_code == 404
    assert r.json()["api"] == "/docs"


def test_a_raiz_serve_o_index_quando_ele_existe(client, tmp_path, monkeypatch):
    pagina = STATIC_DIR / "index.html"
    ja_existia = pagina.is_file()
    if not ja_existia:
        pagina.write_text("<h1>LeadDesk</h1>", encoding="utf-8")

    try:
        r = client.get("/")

        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
    finally:
        if not ja_existia:
            pagina.unlink()


def test_o_mount_estatico_serve_arquivo_de_asset(client):
    asset = STATIC_DIR / "_teste.css"
    asset.write_text("body{margin:0}", encoding="utf-8")

    try:
        r = client.get("/static/_teste.css")

        assert r.status_code == 200
        assert "margin:0" in r.text
    finally:
        asset.unlink()


def test_asset_inexistente_devolve_404(client):
    assert client.get("/static/nao-existe.css").status_code == 404


def test_o_mount_nao_sombreia_as_rotas_de_negocio(client, make_lead):
    """As rotas foram registradas antes do mount — têm precedência."""
    make_lead()

    assert client.get("/leads/").status_code == 200
    assert client.get("/prospects/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 200


def test_a_raiz_fica_fora_do_schema_da_api(client):
    caminhos = client.get("/openapi.json").json()["paths"]

    assert "/" not in caminhos
    assert "/leads/" in caminhos
