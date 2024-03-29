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


def get_maxPosition(ship,hlt_map,planned_position, game):
    max_value = [0.0,1.0,2.0]
    max_key = {0.0:(0,0),1.0:(0,0),2.0:(0,0)}
    for k in hlt_map:
        min_max = min(max_value)
        if k not in planned_position and hlt_map[k] > min_max:
            if hlt_map[k] not in max_key:
                max_key[hlt_map[k]] = k
                min_idx = max_value.index(min(max_value))
                max_value[min_idx] = hlt_map[k]
            else:
                c = 0.01
                while hlt_map[k]+c in max_key:
                    c += c
                max_key[hlt_map[k]+c] = k
                min_idx = max_value.index(min(max_value))
                max_value[min_idx] = hlt_map[k]+c 
            del max_key[min_max]
                    
    max_reward = 10000
    desired_position = ship.position

    for key, position in max_key.items():
        p = hlt.Position(position[0], position[1])
        nav = game.game_map.aStar_plan(ship.position,p)
        home_nav = game.game_map.aStar_plan(p,me.shipyard.position)
        position_cost = (nav['cost']+home_nav['cost'])/hlt_map[position]
        if position_cost < max_reward:
            max_reward = position_cost
            desired_position = p
    return desired_position


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
            amount = 0
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

initial_moveCost = 1
end_moveCost = 30
plateau = 0.42*constants.MAX_TURNS
m = (math.log(end_moveCost) - math.log(initial_moveCost))/(constants.MAX_TURNS - plateau)
b = initial_moveCost*math.exp(-m)

# pre compute needed stuff here before intializing game
# Respond with your name. 
game.ready("pyBot")
mission = {}
next_location = {}
prev_location = {}
current_location = {}
built_drop = False


while True:
    # Get the latest game state.
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    if game.turn_number > plateau:
        y = b*math.exp(m*game.turn_number)/4
        y2 = y/4 - constants.MAX_TURNS/game.turn_number
        if y2 < initial_moveCost:
            y2 = initial_moveCost
    else:
        y = initial_moveCost
        y2 = y

    # A command queue holds all the commands you will run this turn.
    command_queue = []
    planned_position = []
    shipyard_attack = False

    for ship in me.get_ships():
        ship_map = scoreMap(game,ship.position,ship.position)
        ship_map[(ship.position.x,ship.position.y)] = game_map[ship.position].halite_amount
        for key in ship_map:
            hlt_map[key] = ship_map[key]

        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"  

        if (constants.MAX_TURNS - game.turn_number - 16) <= game_map.calculate_distance(ship.position,me.shipyard.position):
            ship_status[ship.id] = "end of game"
        elif ship.halite_amount >= constants.MAX_HALITE *0.70:
            ship_status[ship.id] = "returning"
            if ship.id in mission:
                del mission[ship.id]

        if (me.halite_amount+ship.halite_amount) > y2*constants.DROPOFF_COST and game_map.calculate_distance(ship.position,me.shipyard.position) >= (4/3)*r and not built_drop:
                built_drop = True
                command_queue.append(ship.make_dropoff())
                logging.info("Ship {} is being turned into a dropoff.".format(ship.id))
        elif ship_status[ship.id] == "exploring":
            if ship.id not in mission:
                maxP = get_maxPosition(ship,hlt_map,planned_position,game)
            # if game_map[maxP].halite_amount > y*game_map[ship.position].halite_amount:
                move = game_map.aStar_navigate(ship, maxP)

                next_ = ship.position + hlt.Position(move[0],move[1])
                next_location[ship.id] = (next_.x,next_.y)
                if game.turn_number > 1 and ship.id in current_location:
                    prev_location[ship.id] = current_location[ship.id]
                    if prev_location[ship.id] == next_location[ship.id]:
                        move = (0,0)
                current_location[ship.id] = (ship.position.x,ship.position.y)

                command_queue.append(ship.move(move))
                planned_position.append((maxP.x,maxP.y))
                mission[ship.id] = (maxP.x,maxP.y)                
                
            else:
                maxP = hlt.Position(mission[ship.id][0],mission[ship.id][1])
                move = game_map.aStar_navigate(ship, maxP)
                command_queue.append(ship.move(move))
                planned_position.append(mission[ship.id])
                if game_map[maxP].halite_amount <= 15:
                    del mission[ship.id]
            logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                ship.id, ship.halite_amount, ship_status[ship.id], maxP, ship.position, move))

        elif ship_status[ship.id] == "returning":
            for dropoff in me.get_dropoffs():
                if ship.position == dropoff.position:
                    ship_status[ship.id] = "exploring"

            if ship.position == me.shipyard.position:
                ship_status[ship.id] = "exploring"

            else:
                curCost = 10000000
                for dropoff in me.get_dropoffs():
                    newDropoff = game_map.aStar_plan(ship.position, dropoff.position)
                    newCost = newDropoff['cost']
                    if newCost < curCost:
                        curCost = newCost
                        drop = dropoff

                shipyardNav = game_map.aStar_plan(ship.position, me.shipyard.position)
                shipyardCost = shipyardNav['cost']

                if shipyardCost < curCost:
                    return_location = me.shipyard
                else:
                    return_location = drop

                crash = False
                if game_map[return_location.position].is_occupied  and game_map[return_location.position].ship.owner != me.id and not shipyard_attack:
                    crash = True
                    shipyard_attack = True
                move = game_map.aStar_navigate(ship, return_location.position, crash)
                command_queue.append(ship.move(move))
                logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                    ship.id, ship.halite_amount, ship_status[ship.id], return_location.position, ship.position, move))

        elif ship_status[ship.id] == "end of game":
            curCost = 10000000
            for dropoff in me.get_dropoffs():
                newDropoff = game_map.aStar_plan(ship.position, dropoff.position)
                newCost = newDropoff['cost']
                if newCost < curCost:
                    curCost = newCost
                    drop = dropoff

            shipyardNav = game_map.aStar_plan(ship.position, me.shipyard.position)
            shipyardCost = shipyardNav['cost']

            if shipyardCost < curCost:
                return_location = me.shipyard
            else:
                return_location = drop

            move = game_map.aStar_navigate(ship, return_location.position,True)
            command_queue.append(ship.move(move))
            # planned_position.append((ship.position.x,ship.position.y))
            logging.info("Ship {} has {} halite and is {} to {} from {} by moving {}.".format(
                    ship.id, ship.halite_amount, ship_status[ship.id], return_location.position, ship.position, move))


    # If you're on the first turn and have enough halite, spawn a ship. 10*(len(me.get_dropoffs())+1) >= len(me.get_ships())
    # Don't spawn a ship if you currently have a ship at port, though. game.turn_number <= 0.5*constants.MAX_TURNS
    if me.halite_amount >= y*constants.SHIP_COST and not game_map[me.shipyard].is_occupied or len(me.get_ships()) == 0 and me.halite_amount >= constants.SHIP_COST:
        command_queue.append(game.me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
