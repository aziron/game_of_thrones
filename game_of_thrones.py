import requests
import threading
import logging
from time import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HOUSE_URL = "https://anapioficeandfire.com/api/houses/%i"
CHARACTER_URL = "https://anapioficeandfire.com/api/characters/%i"
init_houses = []
updated_houses = {}
characters_global = {}

class House:
    house_counter = 0
    def __init__(self):
        House.house_counter += 1
        self.id = House.house_counter
        self.name = ""
        self.sworn_members = []
    
    def update_data(self):
        resp = requests.get(HOUSE_URL % self.id)
        data = resp.json()
        self.set_name(data["name"])
        for url in data["swornMembers"]:
            sworn_member_id = int(url.split("/")[-1])
            self.sworn_members.append(sworn_member_id)
    
    def get_id(self):
        return self.id

    def get_sworn_members(self):
        characters = []
        character_names = []
        m_threads = []
        for character_id in self.sworn_members:
            if character_id in characters_global:
                characters.append(characters_global[character_id])
            else:
                character = Character(character_id)
                t = threading.Thread(target=character.update_data)
                m_threads.append(t)
                t.start()
                characters.append(character)
                characters_global[character_id] = character
        [ t.join() for t in m_threads ]
        for character in characters:
            character_names.append(character.get_name())
        return character_names

    def set_name(self, name):
        self.name = name
    
    def get_name(self):
        return self.name

    def set_sworn_member(self, sworn_member):
        self.sworn_members.add(sworn_member)


class Character:
    def __init__(self, character_id):
        self.id = character_id
        self.name = ""
    
    def update_data(self):
        resp = requests.get(CHARACTER_URL % self.id)
        data = resp.json()
        self.set_name(data)
    
    def get_name(self):
        return self.name

    def get_id(self):
        return self.id
    
    def set_name(self, data):
        if data["name"] != "":
            self.name = data["name"]
        else:
            self.name = data["aliases"][0]

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response()
        self.wfile.write("<div style=\"display: table-cell\">".encode('utf-8'))
        self.wfile.write("<h1>Houses:</h1>".encode('utf-8'))
        for i in range(len(updated_houses)):
            house_id = updated_houses[i+1].get_id()
            house_name = updated_houses[i+1].get_name()
            self.wfile.write("<li><a href=\"/{0}\"> {1}</a></li>".format(house_id, house_name).encode('utf-8'))
        self.wfile.write("</div>".encode('utf-8'))
        self.wfile.write("<div style=\"display: table-cell\">".encode('utf-8'))
        self.wfile.write("<h1>House Members:</h1>".encode('utf-8'))
        if self.get_number(self.path):
            i = self.get_number(self.path)
            sworn_members = updated_houses[i].get_sworn_members()
            if len(sworn_members) == 0:
                self.wfile.write("<p>No members found in this House</p>".encode('utf-8'))
            for character in sworn_members:
                self.wfile.write("<li> {0}</li>".format(character).encode('utf-8'))
        self.wfile.write("</div>".encode('utf-8'))

    def get_number(self, s):
        try:
            return int(s[1:])
        except ValueError:
            return False

def downloader():
    global init_houses
    while len(init_houses) > 0:
        house = init_houses.pop()
        house.update_data()
        i = house.get_id()
        updated_houses[i] = house

def run_server(server_class=HTTPServer, handler_class=S):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    threads = []
    nthreads = 32
    nhouses = 444
    for i in range(nhouses):
        init_houses.append(House())

    for i in range(nthreads):
        t = threading.Thread(target=downloader)
        threads.append(t)

    ts = time()
    [ t.start() for t in threads ]
    [ t.join() for t in threads ]
    elapsed = time() - ts
    
    print("Preparing data took {0:.3f} seconds".format(elapsed))
    run_server()