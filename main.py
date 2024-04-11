import os
import urllib.parse

import requests
import tabulate
from bs4 import BeautifulSoup
from collections import namedtuple

Game = namedtuple("Game", ("id", "home", "away", "quotes"))
Prediction = namedtuple("Prediction", ("game", "home", "away"))


def main():
    username = os.environ["KICKTIPP_USER"]
    password = os.environ["KICKTIPP_PASSWORD"]
    tipprunde = os.environ["KICKTIPP_TIPPRUNDE"]

    kicktipp = Kicktipp(username, password, tipprunde)
    kicktipp.tipp(PredictionStrategy())


class Kicktipp:
    def __init__(self, username, password, tipprunde):
        self._username = username
        self._password = password
        self._client = Client(tipprunde)

    def tipp(self, predicition_strategy):
        self._client.login(self._username, self._password)
        tipper_id, tippsaison_id, games = self._client.get_tippabgabe()

        predictions = [predicition_strategy.predict_game(game) for game in games]
        self.print_predictions(predictions)

        success = self._client.send_predictions(predictions, tipper_id, tippsaison_id)
        if not success:
            print("Predictions could not be sent.")

    def print_predictions(self, predictions):
        data = [(p.game.home, p.game.away, f"{p.home} : {p.away}") for p in predictions]
        table = tabulate.tabulate(data, headers=("Home", "Away", "Score"))
        print(table)


class PredictionStrategy:
    def __init__(self, base=5):
        self._base = base

    def predict_game(self, game: Game) -> Prediction:
        home, draw, away = tuple((100 / q) / 100 for q in game.quotes)

        if draw > home and draw > away:
            return Prediction(game, 1, 1)

        home_goals = int(self._base * home)
        away_goals = int(self._base * away)

        return Prediction(game, home_goals, away_goals)


class Client:
    def __init__(self, tipprunde, base_url="https://www.kicktipp.de"):
        self._session = requests.Session()
        self._base_url = base_url
        self._login_url = base_url + "/info/profil/loginaction"
        self._tipp_url = base_url + f"/{tipprunde}/tippabgabe"

        self._headers = {"Content-Type": "application/x-www-form-urlencoded"}

    def login(self, username: str, password: str):
        # make request of base url to start JSESSION with server
        self._session.get(self._base_url)

        # login to create cookie
        data = {
            "kennung": username,
            "passwort": password,
            "submitbutton": "Anmelden",
            "_charset_": "UTF-8"
        }
        response = self._session.post(self._login_url, headers=self._headers, data=self._to_form_data(data))

    def get_tippabgabe(self):
        # request tippabgabe site
        response = self._session.get(self._tipp_url)
        if response.status_code != 200:
            raise ValueError("Fehler beim Laden der Tippseite!")

        # parse games from html input table
        soup = BeautifulSoup(response.content, features="html.parser")

        tipper_id = soup.find("input", {"name": "tipperId"}).get("value")
        tippsaison_id = soup.find("input", {"name": "tippsaisonId"}).get("value")

        table = soup.find("table", {"id": "tippabgabeSpiele"})
        games = [self._parse_game(table_row) for table_row in table.find("tbody").find_all("tr")]

        return tipper_id, tippsaison_id, games

    def send_predictions(self, predictions, tipper_id, tippsaison_id):
        data = {
            "tipperId": tipper_id,
            "tippsaisonId": tippsaison_id,
            "bonus": "false",
            "submitbutton": "Tipps+speichern",
            "_charset_": "UTF-8"
        }

        for prediction in predictions:
            key = f"spieltippForms%5B{prediction.game.id}%5D"
            data[key + ".tippAbgegeben"] = "true"
            data[key + ".heimTipp"] = str(prediction.home)
            data[key + ".gastTipp"] = str(prediction.away)

        response = self._session.post(self._tipp_url, headers=self._headers, data=self._to_form_data(data))
        return response.status_code == 200

    def _to_form_data(self, data: dict) -> str:
        encoded_dict = {key: urllib.parse.quote_plus(value) for key, value in data.items()}
        return "&".join(f"{key}={value}" for key, value in encoded_dict.items())

    def _parse_game(self, table_row) -> Game:
        table_data = table_row.find_all("td")
        game_id = table_data[3].find_all("input")[0].get("id")[15:-14]
        home = table_data[1].text
        away = table_data[2].text
        quotes = tuple(float(n.strip()) for n in table_data[4].text.removeprefix("Quote: ").split('/'))

        return Game(game_id, home, away, quotes)


if __name__ == '__main__':
    main()
