"""Regole del gioco "indovina il numero", separate da AWS: le tabelle e l'invio dei messaggi WebSocket
arrivano dall'esterno (boto3 nelle Lambda, oggetti finti nei test).

Regole (valori nelle costanti sotto, come nell'esempio CloudFormation):
- un giocatore si iscrive con un nickname (5-30 lettere o cifre) e un numero da 1 a 99 non scelto da altri
- il numero si puo' cambiare solo una volta ogni 24 ore
- ogni giorno si possono fare al massimo 5 tentativi di indovinare il numero di un altro giocatore
- numero indovinato: chi attacca prende 1 punto, chi lo aveva perde 3 punti, resta senza numero e puo'
  sceglierne subito un altro; tutti i giocatori collegati ricevono la notizia; la partita va nello storico
- tentativo sbagliato: chi attacca perde 1 punto
- i giocatori bannati dall'amministratore non possono piu' giocare
"""

import uuid
from datetime import datetime, timedelta, timezone

NUMBER_MIN, NUMBER_MAX = 1, 99
CHANGE_HOURS = 24
MAX_GUESSES_PER_DAY = 5
HIT_POINTS, PENALTY_POINTS, MISS_POINTS = 1, 3, 1
INACTIVITY_DAYS = 10
LOG_DAYS = 30


class GameError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def now() -> datetime:
    return datetime.now(timezone.utc)


def valid_nickname(nickname) -> bool:
    return isinstance(nickname, str) and 5 <= len(nickname) <= 30 and nickname.isalnum()


def _number(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not NUMBER_MIN <= value <= NUMBER_MAX:
        raise GameError(400, f"Il numero deve essere un intero da {NUMBER_MIN} a {NUMBER_MAX}")
    return value


class Game:
    """tables: oggetto con gli attributi players, matches, logs, bans (tabelle DynamoDB o finte);
    send(connection_id, message) -> bool: invia un messaggio WebSocket, False se il client non c'e' piu'."""

    def __init__(self, tables, send):
        self.t = tables
        self.send = send

    # ---- utilita' ----
    def log(self, nickname: str, message: str) -> None:
        ts = now()
        self.t.logs.put_item(Item={
            "day": ts.strftime("%Y-%m-%d"), "ts": f"{ts.isoformat()}#{uuid.uuid4().hex[:6]}",
            "nickname": nickname, "message": message,
            "expiresAt": int((ts + timedelta(days=LOG_DAYS)).timestamp()),  # TTL di DynamoDB
        })

    def players(self) -> list:
        return _scan(self.t.players)

    def player(self, nickname: str):
        return self.t.players.get_item(Key={"nickname": nickname}).get("Item")

    def is_banned(self, nickname: str) -> bool:
        return "Item" in self.t.bans.get_item(Key={"nickname": nickname})

    def notify(self, player, message: dict) -> None:
        """Messaggio a un giocatore collegato; se la connessione non esiste piu' la toglie."""
        cid = player.get("connectionId") if player else None
        if cid and not self.send(cid, message):
            self.t.players.update_item(Key={"nickname": player["nickname"]}, UpdateExpression="REMOVE connectionId")

    def broadcast(self, message: dict) -> int:
        sent = 0
        for p in self.players():
            if p.get("connectionId"):
                self.notify(p, message)
                sent += 1
        return sent

    # ---- giocatori ----
    def set_number(self, nickname, number) -> str:
        if not valid_nickname(nickname):
            raise GameError(400, "Nickname non valido (5-30 caratteri, solo lettere e cifre)")
        number = _number(number)
        if self.is_banned(nickname):
            raise GameError(403, f"{nickname} e' stato bannato")
        taken = next((p for p in self.players() if int(p.get("number", 0)) == number and p["nickname"] != nickname), None)
        if taken:
            raise GameError(409, "Numero gia' scelto da un altro giocatore: scegline un altro")

        ts = now()
        player = self.player(nickname)
        if player:
            last = datetime.fromisoformat(player["lastUpdate"])
            wait = last + timedelta(hours=CHANGE_HOURS) - ts
            if wait.total_seconds() > 0:
                raise GameError(429, f"Puoi cambiare numero una volta ogni {CHANGE_HOURS} ore: riprova tra {int(wait.total_seconds() // 3600) + 1} ore")
            self.t.players.update_item(Key={"nickname": nickname},
                UpdateExpression="SET #n = :n, lastUpdate = :ts",
                ExpressionAttributeNames={"#n": "number"}, ExpressionAttributeValues={":n": number, ":ts": ts.isoformat()})
            self.log(nickname, "ha cambiato numero")
            return f"Numero cambiato in {number}"
        self.t.players.put_item(Item={"nickname": nickname, "number": number, "score": 0, "guesses": {},
                                      "lastUpdate": ts.isoformat(), "createdAt": ts.isoformat()})
        self.log(nickname, "si e' iscritto al gioco")
        self.broadcast({"event": "join", "nickname": nickname})
        return f"{nickname} iscritto con il numero {number}"

    def guess(self, attacker, guess) -> dict:
        guess = _number(guess)
        player = self.player(attacker) if valid_nickname(attacker) else None
        if not player:
            raise GameError(404, "Giocatore non iscritto")
        if self.is_banned(attacker):
            raise GameError(403, f"{attacker} e' stato bannato")
        if int(player.get("number", 0)) == guess:
            raise GameError(400, "Questo e' il tuo numero")

        today = now().strftime("%Y-%m-%d")
        guesses = {k: int(v) for k, v in player.get("guesses", {}).items() if k == today}  # tiene solo oggi
        if guesses.get(today, 0) >= MAX_GUESSES_PER_DAY:
            raise GameError(429, f"Hai finito i {MAX_GUESSES_PER_DAY} tentativi di oggi")
        guesses[today] = guesses.get(today, 0) + 1
        left = MAX_GUESSES_PER_DAY - guesses[today]

        targets = [p for p in self.players() if p["nickname"] != attacker and int(p.get("number", 0)) == guess]
        if not targets:
            self._add_score(attacker, -MISS_POINTS, guesses)
            self.log(attacker, f"ha provato il {guess}: nessuno")
            return {"hit": False, "message": f"Numero sbagliato: -{MISS_POINTS} punto. Tentativi rimasti oggi: {left}",
                    "left": left}

        target = targets[0]  # i numeri sono unici: al massimo un giocatore
        ts = now()
        self._add_score(attacker, HIT_POINTS, guesses)
        # chi e' stato colpito resta senza numero e puo' sceglierne subito un altro (lastUpdate retrodatato)
        self.t.players.update_item(Key={"nickname": target["nickname"]},
            UpdateExpression="SET #n = :zero, lastUpdate = :old, score = if_not_exists(score, :zero) - :p",
            ExpressionAttributeNames={"#n": "number"},
            ExpressionAttributeValues={":zero": 0, ":p": PENALTY_POINTS,
                                       ":old": (ts - timedelta(hours=CHANGE_HOURS, minutes=1)).isoformat()})
        self.t.matches.put_item(Item={"matchId": f"{ts.isoformat()}#{uuid.uuid4().hex[:6]}", "timestamp": ts.isoformat(),
                                      "winner": attacker, "loser": target["nickname"], "numberGuessed": guess})
        self.log(attacker, f"ha indovinato il numero di {target['nickname']}")
        self.log(target["nickname"], f"ha perso {PENALTY_POINTS} punti: {attacker} ha indovinato il suo numero")
        self.notify(target, {"event": "hit", "by": attacker,
                             "message": f"{attacker} ha indovinato il tuo numero: -{PENALTY_POINTS} punti, scegli un nuovo numero"})
        self.broadcast({"event": "match", "winner": attacker, "loser": target["nickname"], "number": guess})
        return {"hit": True, "message": f"Hai indovinato il numero di {target['nickname']}: +{HIT_POINTS} punto", "left": left}

    def _add_score(self, nickname: str, points: int, guesses: dict) -> None:
        self.t.players.update_item(Key={"nickname": nickname},
            UpdateExpression="SET score = if_not_exists(score, :zero) + :p, guesses = :g",
            ExpressionAttributeValues={":zero": 0, ":p": points, ":g": guesses})

    # ---- WebSocket ----
    def connect(self, nickname, connection_id: str) -> None:
        if not valid_nickname(nickname) or not self.player(nickname):
            raise GameError(404, "Giocatore non iscritto: prima scegli un numero")
        if self.is_banned(nickname):
            raise GameError(403, "Giocatore bannato")
        self.t.players.update_item(Key={"nickname": nickname}, UpdateExpression="SET connectionId = :c",
                                   ExpressionAttributeValues={":c": connection_id})
        self.log(nickname, "si e' collegato")

    def disconnect(self, connection_id: str) -> None:
        for p in self.players():
            if p.get("connectionId") == connection_id:
                self.t.players.update_item(Key={"nickname": p["nickname"]}, UpdateExpression="REMOVE connectionId")
                self.log(p["nickname"], "si e' scollegato")

    # ---- letture ----
    def scores(self) -> list:
        return sorted(({"nickname": p["nickname"], "score": int(p.get("score", 0)), "playing": int(p.get("number", 0)) > 0,
                        "connected": bool(p.get("connectionId")), "lastUpdate": p.get("lastUpdate")}
                       for p in self.players()), key=lambda p: (-p["score"], p["nickname"]))

    def matches(self) -> list:
        return sorted(_scan(self.t.matches), key=lambda m: m["timestamp"], reverse=True)

    def logs(self, limit: int = 100) -> list:
        items = []
        for days_ago in (0, 1):  # oggi e ieri
            day = (now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            items += self.t.logs.query(KeyConditionExpression=_eq("day", day), ScanIndexForward=False, Limit=limit)["Items"]
        return sorted(items, key=lambda i: i["ts"], reverse=True)[:limit]

    # ---- amministrazione ----
    def ban(self, nickname, reason: str) -> str:
        if not valid_nickname(nickname):
            raise GameError(400, "Nickname non valido")
        reason = (reason or "nessun motivo").strip()[:200]
        player = self.player(nickname)
        if player:  # avvisa prima di cancellarlo (nel CloudFormation lo cercava dopo averlo cancellato)
            self.notify(player, {"event": "ban", "reason": reason})
            self.t.players.delete_item(Key={"nickname": nickname})
        self.t.bans.put_item(Item={"nickname": nickname, "reason": reason, "bannedAt": now().isoformat()})
        self.log(nickname, f"bannato dall'amministratore: {reason}")
        return f"{nickname} bannato: {reason}"

    def unban(self, nickname) -> str:
        self.t.bans.delete_item(Key={"nickname": nickname})
        self.log(nickname, "non e' piu' bannato")
        return f"{nickname} puo' di nuovo giocare"

    def bans(self) -> list:
        return _scan(self.t.bans)

    def reset_numbers(self) -> int:
        old = (now() - timedelta(hours=CHANGE_HOURS, minutes=1)).isoformat()
        count = 0
        for p in self.players():
            self.t.players.update_item(Key={"nickname": p["nickname"]},
                UpdateExpression="SET #n = :zero, lastUpdate = :old", ExpressionAttributeNames={"#n": "number"},
                ExpressionAttributeValues={":zero": 0, ":old": old})
            count += 1
        self.log("admin", "ha azzerato tutti i numeri")
        self.broadcast({"event": "reset", "message": "L'amministratore ha azzerato i numeri: scegline uno nuovo"})
        return count

    def cleanup_inactive(self) -> list:
        """Toglie i giocatori che non cambiano numero da piu' di INACTIVITY_DAYS giorni."""
        cutoff = now() - timedelta(days=INACTIVITY_DAYS)
        removed = []
        for p in self.players():
            if datetime.fromisoformat(p["lastUpdate"]) < cutoff:
                self.t.players.delete_item(Key={"nickname": p["nickname"]})
                self.log(p["nickname"], f"tolto dal gioco dopo {INACTIVITY_DAYS} giorni di inattivita'")
                removed.append(p["nickname"])
        return removed


def _eq(name, value):
    from boto3.dynamodb.conditions import Key
    return Key(name).eq(value)


def _scan(table) -> list:
    items, kwargs = [], {}
    while True:
        page = table.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
