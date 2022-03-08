import asyncio
import getpass
import json
import os

import websockets

from shape import SHAPES

import copy

#NAME=brunoc python3 student.py

#source: https://levelup.gitconnected.com/tetris-ai-in-python-bd194d6326ae
#source: https://codemyroad.wordpress.com/2013/04/14/tetris-ai-the-near-perfect-player/



async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                state = json.loads(
                    await websocket.recv() 
                )  # receive game update, this must be called timely or your game will get out of sync with the server
                
                key = ""

                if state.get("game") != None and state.get("piece") != None:
                    keys = bestKeys(best_rotation_position(state.get("game"),state.get("piece")))
                    while keys != []:
                        key = keys.pop(0)
                        json.loads(await websocket.recv())
                        await websocket.send(json.dumps({"cmd": "key", "key": key}) )
                    
                await websocket.send(
                    json.dumps({"cmd": "key", "key": key})
                )  # send key command to server - you must implement this send in the AI agent
            
            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return


#checks if piece intersects grid
def intersectsGrid(piece,x,y):
    if piece == None:
        return None
    intersection = False
    for i in piece:
        if (i[0] + x < 1 or i[0] + x > 8 or i[1] + y > 29):
            intersection = True
    return intersection


#checks if piece intersects game
def intersectsGame(game,piece,x,y):
    if piece == None:
        return None
    lista = []
    for p in piece:
        lista.append([p[0]+x,p[1]+y])
    return any(l in game for l in lista)


#[collumn, height]: [0,5] -> collumn 0 has 5 'height'
def maxList(lista):
    l = []
    for counter in range(1,9):
        tmp = 30
        for e in lista:
            if e[0] == counter:
                if e[1] < tmp:
                    tmp = e[1]
        l.append([counter,tmp])
    for e in l:
        e[1] = 30 - e[1]
    return l


def soma(lista):
    if lista == []:
        return 0
    return lista[0][1] + soma(lista[1:])


def highest(lista):
    if lista == []:
        return None
    lista.sort(key=lambda x: x[1])
    return lista[0][1]


#how “high” the game is
def aggregateHeight(game):
    return soma(maxList(game))


#The bumpiness of a grid tells us the variation of its column heights
#It is computed by summing up the absolute differences between all two adjacent columns
def bumpiness(lista):
    if len(lista) == 1:
        return 0
    return abs(lista[0][1] - lista[1][1]) + bumpiness(lista[1:])


#Number of holes of a given list
#A hole is an unfilled square, whose y is <= game height (y is < game height ?).     
def holes(game):
    nholes = 0
    high = highest(game)
    if high != None:
        for i in range(1,9):
            for j in range(29, high-1, -1): #high better then high-1?
                if [i,j] not in game:
                    nholes += 1
    return nholes


################## heuristic() not working as expected ##################
def holes2(game):
    nholes = 0
    max = maxList(game)
    for i in range(1,9):
        for j in range(29,30-max[i-1][1],-1):
            if [i,j] not in game:
                nholes += 30-j
    return nholes


def holesRight(game):
    if len(game) < 2:
        return 0
    x = game[1][1] - game[0][1]
    if x > 0:
        return x + holesRight(game[1:])
    else:
        return holesRight(game[1:])


def holesLeft(game):
    if len(game) < 2:
        return 0
    x = game[len(game)-2][1] - game[len(game)-1][1]
    if x > 0:
        return x + holesLeft(game[:-1])
    else:
        return holesLeft(game[:-1])


def totalHoles(game):
    max = maxList(game)
    return holes2(game) + holesRight(max) + holesLeft(max)
########################################################################


#The number of completed lines in game
def completeLines(game):
    h = highest(game)
    totalLines = 0
    if h != None:
        for j in range(29,h-1,-1):
            counter = 0
            for i in range(1,9):
                if [i,j] in game:
                    counter += 1
            if counter == 8:
                totalLines += 1
    return totalLines


#a new 'game' with a current piece is returned
def simulateGravity(game,piece,x):
    y = 1
    while not intersectsGame(game,piece,x,y) and not intersectsGrid(piece,x,y):
        y += 1
    lista = []
    for e in piece:
        lista.append([e[0]+x,e[1]+y-1])
    l = game + lista
    return l


#values might be changed
def heuristic(game):
    a = -0.79
    b =  0.82
    c = -0.10
    d = -0.25
    return d * bumpiness(maxList(game)) + a * aggregateHeight(game) + c * holes(game) + b * completeLines(game) 


#heuristic2 is applied to "I" piece
#values might be changed
def heuristic2(game):
    a = -0.69
    b =  0.82
    c = -0.04
    d = -0.10
    return d * bumpiness(maxList(game)) + a * aggregateHeight(game) + c * holes(game) + b * completeLines(game)


#words were exchanged with 89330
def originalShape(piece):
    #S
    if piece == [[4, 2], [4, 3], [5, 3], [5, 4]]:
        original = SHAPES[0]
    #Z
    elif piece == [[4, 2], [3, 3], [4, 3], [3, 4]]:
        original = SHAPES[1]
    #I
    elif piece == [[2, 2], [3, 2], [4, 2], [5, 2]]:
        original = SHAPES[2]
    #O
    elif piece == [[3, 3], [4, 3], [3, 4], [4, 4]]:
        original = SHAPES[3]
    #J
    elif piece == [[4, 2], [5, 2], [4, 3], [4, 4]]:
        original = SHAPES[4]
    #T
    elif piece == [[4, 2], [4, 3], [5, 3], [4, 4]]:
        original = SHAPES[5]
    #L
    elif piece == [[4, 2], [4, 3], [4, 4], [5, 4]]:
        original = SHAPES[6]
    #
    else:
        return []
    
    return original


def best_rotation_position(game,piece):
    original = originalShape(piece)
    if original != []:
        figure = copy.deepcopy(original)
        figure.translate(2,1)
        best = {'heuristic': None, 'position': 0, 'rotation': 0}
        for rotation in range(len(figure.plan)):
            fig = [[x,y] for (x,y) in figure.positions]
            for j in range(-3,8):
                newgame = simulateGravity(game,fig,j)
                if figure.name == "I":
                    h = heuristic2(newgame)
                else:
                    h = heuristic(newgame)
                if best.get('heuristic') == None or h > best.get('heuristic'):
                    best['heuristic'] = h
                    best['position'] = j
                    best['rotation'] = rotation
            figure.rotate()
        return best
    return []


def bestKeys(best_rotation_pos):
    keys = []
    if best_rotation_pos != []:
        best_rotation = best_rotation_pos.get('rotation')
        best_position = best_rotation_pos.get('position')
        rotation = 0
        while rotation < best_rotation:
            keys.append("w")
            rotation += 1
        if best_position < 0:
            l = 0
            while l < abs(best_position):
                keys.append("a")
                l += 1
        elif best_position > 0:
            r = 0
            while r < best_position:
                keys.append("d")
                r += 1
        keys.append("s")
    return keys


# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))
