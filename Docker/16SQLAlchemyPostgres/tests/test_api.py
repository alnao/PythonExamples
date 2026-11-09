"""Test delle API: girano su SQLite in memoria oppure su PostgreSQL (vedi conftest.py)."""
import pytest


def test_stato(client):
    assert client.get("/").json()["stato"] == "ok"


# ---------- autori ----------

def test_crea_e_leggi_autore(client, calvino):
    risposta = client.get(f"/autori/{calvino['id']}")
    assert risposta.status_code == 200
    assert risposta.json() | {"libri": []} == calvino | {"libri": []}


def test_autore_duplicato_viola_unique(client, calvino):
    risposta = client.post("/autori", json={"nome": "Italo", "cognome": "Calvino"})
    assert risposta.status_code == 409


def test_autore_inesistente(client):
    assert client.get("/autori/999").status_code == 404


@pytest.mark.parametrize("dati", [{"nome": "", "cognome": "X"}, {"nome": "X"}, {"nome": "X", "cognome": "Y", "nato_il": "ieri"}])
def test_autore_non_valido(client, dati):
    assert client.post("/autori", json=dati).status_code == 422     # validazione Pydantic


def test_lista_autori_con_conteggio_libri(client, calvino, crea_libro):
    crea_libro()
    crea_libro(titolo="Le città invisibili")
    client.post("/autori", json={"nome": "Primo", "cognome": "Levi"})
    autori = {a["cognome"]: a["numero_libri"] for a in client.get("/autori").json()}
    assert autori == {"Calvino": 2, "Levi": 0}


def test_elimina_autore_cancella_anche_i_libri(client, calvino, crea_libro):
    libro = crea_libro()
    assert client.delete(f"/autori/{calvino['id']}").status_code == 204
    assert client.get(f"/libri/{libro['id']}").status_code == 404


# ---------- libri ----------

def test_crea_libro_con_categorie(crea_libro):
    libro = crea_libro(categorie=["Romanzo", "classici", "romanzo"])
    assert libro["autore"]["cognome"] == "Calvino"
    assert [c["nome"] for c in libro["categorie"]] == ["classici", "romanzo"]   # minuscole, senza doppioni


def test_categorie_riusate_tra_libri(client, crea_libro):
    primo = crea_libro(categorie=["classici"])
    secondo = crea_libro(titolo="Altro", categorie=["classici"])
    assert primo["categorie"][0]["id"] == secondo["categorie"][0]["id"]


def test_isbn_duplicato(client, crea_libro, calvino):
    libro = crea_libro()
    risposta = client.post("/libri", json={"titolo": "Copia", "isbn": libro["isbn"], "anno": 2000,
                                           "prezzo": "5", "autore_id": calvino["id"]})
    assert risposta.status_code == 409


def test_libro_con_autore_inesistente(client):
    risposta = client.post("/libri", json={"titolo": "X", "isbn": "9780000000000", "anno": 2000,
                                           "prezzo": "5", "autore_id": 999})
    assert risposta.status_code == 404


@pytest.mark.parametrize(("campo", "valore"), [("isbn", "123"), ("anno", 1000), ("prezzo", "0"), ("copie", -1)])
def test_libro_non_valido(client, calvino, campo, valore):
    dati = {"titolo": "X", "isbn": "9780000000000", "anno": 2000, "prezzo": "5",
            "autore_id": calvino["id"], campo: valore}
    assert client.post("/libri", json=dati).status_code == 422


def test_ricerca_libri(client, crea_libro):
    crea_libro(titolo="Il barone rampante", anno=1957, categorie=["romanzo"])
    crea_libro(titolo="Lezioni americane", anno=1988, categorie=["saggio"])
    crea_libro(titolo="Le città invisibili", anno=1972, categorie=["romanzo"])

    def titoli(**parametri):
        return [l["titolo"] for l in client.get("/libri", params=parametri).json()]

    assert titoli() == ["Il barone rampante", "Le città invisibili", "Lezioni americane"]
    assert titoli(categoria="romanzo") == ["Il barone rampante", "Le città invisibili"]
    assert titoli(anno_da=1970) == ["Le città invisibili", "Lezioni americane"]
    assert titoli(q="BARONE") == ["Il barone rampante"]      # ilike: senza distinzione maiuscole
    assert titoli(q="calvino") == titoli()                   # ricerca anche sul cognome
    assert titoli(limit=1, offset=1) == ["Le città invisibili"]


# ---------- prestiti ----------

def test_prestito_e_restituzione(client, crea_libro):
    libro = crea_libro(copie=1)
    prestito = client.post(f"/libri/{libro['id']}/prestiti", json={"utente": "alberto"})
    assert prestito.status_code == 201
    assert client.get(f"/libri/{libro['id']}/disponibili").json()["disponibili"] == 0

    # l'unica copia è già fuori
    assert client.post(f"/libri/{libro['id']}/prestiti", json={"utente": "valentina"}).status_code == 409

    restituzione = client.post(f"/prestiti/{prestito.json()['id']}/restituzione")
    assert restituzione.status_code == 200
    assert restituzione.json()["restituito_il"] is not None
    assert client.post(f"/prestiti/{prestito.json()['id']}/restituzione").status_code == 409
    assert client.post(f"/libri/{libro['id']}/prestiti", json={"utente": "valentina"}).status_code == 201


def test_prestito_libro_inesistente(client):
    assert client.post("/libri/999/prestiti", json={"utente": "x"}).status_code == 404


# ---------- statistiche ----------

def test_statistiche(client, crea_libro):
    crea_libro(prezzo="10.00", copie=2, categorie=["romanzo", "classici"])
    libro = crea_libro(titolo="Lezioni americane", prezzo="5.50", copie=1, categorie=["saggio", "classici"])
    client.post(f"/libri/{libro['id']}/prestiti", json={"utente": "alberto"})
    statistiche = client.get("/statistiche").json()
    assert statistiche["libri"] == 2
    assert statistiche["autori"] == 1
    assert statistiche["prestiti_aperti"] == 1
    assert statistiche["libri_per_categoria"] == {"classici": 2, "romanzo": 1, "saggio": 1}
    assert float(statistiche["valore_catalogo"]) == pytest.approx(25.50)
    assert statistiche["autore_piu_prolifico"] == "Italo Calvino"
