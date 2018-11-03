#!/usr/bin/env python3

# Import the Halite SDK, which will let you interact with the game.
import hlt
from hlt import constants

import math
import random
import logging
# things to implement:
    # scale number of ships with respect to number of drop off available
    # implement cost of traveling 
    # some how prevent clog up at shipyard
    # navigation - ships can swap positions


def get_maxPosition(hlt_map,planned_position, game_map):
    max_value = 0
    for k in hlt_map:
        if k not in planned_position and not game_map[hlt.Position(k[0],k[1])].is_occupied and hlt_map[k] > max_value:
            max_value = hlt_map[k]
            max_key = k
    return max_key


def get_travelCost():
    print('cost')


def scoreMap(game,start,curPoint,radius=5,hlt_map={}):
    gm = game.game_map
    directions = curPoint.get_surrounding_cardinals()
    for d in directions:
        d = gm.normalize(d)
        pos = (d.x,d.y)
        dist = gm.calculate_distance(start,d)
        if dist > radius:
            return hlt_map
        elif pos not in hlt_map:
            if gm[d].structure == None:
                amount = gm[d].halite_amount
                # gm[d].mark_safe()
            hlt_map[pos] = amount
            htl_map = scoreMap(game,game.me.shipyard.position,d,radius,hlt_map)
    return hlt_map


# This game object contains the initial game state.
game = hlt.Game()
if game.game_map.width > game.game_map.height:
    r =  game.game_map.width/4
else:
    r = game.game_map.height/4
hlt_map = scoreMap(game,game.me.shipyard.position,game.me.shipyard.position,r)
ship_status = {}

initial_moveCost = 10
end_moveCost = 1.21
plateau = 125
m = (math.log(end_moveCost) - math.log(initial_moveCost))/(constants.MAX_TURNS - plateau)
b = initial_moveCost*math.exp(-m)
# pre compute needed stuff here before intializing game
# Respond with your name. 
game.ready("pyBot")

while True:
    # Get the latest game state.
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    if game.turn_number > plateau:
        y = b*math.exp(m*game.turn_number)
    else:
        y = initial_moveCost

    # A command queue holds all the commands you will run this turn.
    command_queue = []
    planned_position = []
    next_position = []

    for ship in me.get_ships():
        ship_map = scoreMap(game,ship.position,ship.position)
        for key in ship_map:
            hlt_map[key] = ship_map[key]

        # logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))
        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"  

        if (constants.MAX_TURNS - game.turn_number - 15) <= game_map.calculate_distance(ship.position,me.shipyard.position):
            ship_status[ship.id] = "end of game"
        elif ship.halite_amount >= constants.MAX_HALITE *0.68:
            ship_status[ship.id] = "returning"

        if ship_status[ship.id] == "exploring":
            max_key = get_maxPosition(hlt_map,planned_position,game_map)
            maxP = hlt.Position(max_key[0],max_key[1])
            if game_map[maxP].halite_amount >= y*game_map[ship.position].halite_amount:
                move = game_map.aStar_navigate(ship, maxP)
                # move = game_map.naive_navigate(ship, maxP)
                command_queue.append(ship.move(move))
                planned_position.append((maxP.x,maxP.y))
                next_location = ship.position + hlt.Position(move[0],move[1])
            else:
                move = 'staying still'
                command_queue.append(ship.stay_still())
                planned_position.append((ship.position.x,ship.position.y))
            logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                ship.id, ship.halite_amount, ship_status[ship.id], maxP, ship.position, move))

        elif ship_status[ship.id] == "returning":
            if ship.position == me.shipyard.position:
                ship_status[ship.id] = "exploring"

            # elif me.halite_amount > constants.DROPOFF_COST:
            #     command_queue.append(ship.make_dropoff())
            #     logging.info("Ship {} is being turned into a dropoff.".format(ship.id, ship_status[ship.id]))

            else:
                # prevYard = 1000000
                # for dropoff in me.get_dropoffs():
                #   newYard = game_map.calculate_distance(ship.position, dropoff.position)
                #   if newYard < prevYard:
                #       prevYard = newYard
                #       shipyard = dropoff
                crash = False
                if game_map[me.shipyard.position].is_occupied  and game_map[me.shipyard.position].ship not in ship_status:
                    crash = True
                move = game_map.aStar_navigate(ship, me.shipyard.position, crash)
                command_queue.append(ship.move(move))
                logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                    ship.id, ship.halite_amount, ship_status[ship.id], me.shipyard.position, ship.position, move))

        elif ship_status[ship.id] == "end of game":
            move = game_map.aStar_navigate(ship, me.shipyard.position,True)
            command_queue.append(ship.move(move))
            # planned_position.append((ship.position.x,ship.position.y))
            logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                    ship.id, ship.halite_amount, ship_status[ship.id], me.shipyard.position, ship.position, move))


    # If you're on the first turn and have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though.
    if game.turn_number <= 0.5*constants.MAX_TURNS and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(game.me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
