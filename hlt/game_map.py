import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .positionals import Direction, Position

class Player:
    """
    Player object containing all items/metadata pertinent to the player.
    """
    def __init__(self, player_id, shipyard, halite=0):
        self.id = player_id
        self.shipyard = shipyard
        self.halite_amount = halite
        self._ships = {}
        self._dropoffs = {}

    def get_ship(self, ship_id):
        """
        Returns a singular ship mapped by the ship id
        :param ship_id: The ship id of the ship you wish to return
        :return: the ship object.
        """
        return self._ships[ship_id]

    def get_ships(self):
        """
        :return: Returns all ship objects in a list
        """
        return self._ships.values()

    def get_dropoff(self, dropoff_id):
        """
        Returns a singular dropoff mapped by its id
        :param dropoff_id: The dropoff id to return
        :return: The dropoff object
        """
        return self._dropoffs[dropoff_id]

    def get_dropoffs(self):
        """
        :return: Returns all dropoff objects in a list
        """
        return self._dropoffs.values()

    def has_ship(self, ship_id):
        """
        Check whether the player has a ship with a given ID.

        Useful if you track ships via IDs elsewhere and want to make
        sure the ship still exists.

        :param ship_id: The ID to check.
        :return: True if and only if the ship exists.
        """
        return ship_id in self._ships


    @staticmethod
    def _generate():
        """
        Creates a player object from the input given by the game engine
        :return: The player object
        """
        player, shipyard_x, shipyard_y = map(int, input().split())
        return Player(player, Shipyard(player, -1, Position(shipyard_x, shipyard_y)))

    def _update(self, num_ships, num_dropoffs, halite):
        """
        Updates this player object considering the input from the game engine for the current specific turn.
        :param num_ships: The number of ships this player has this turn
        :param num_dropoffs: The number of dropoffs this player has this turn
        :param halite: How much halite the player has in total
        :return: nothing.
        """
        self.halite_amount = halite
        self._ships = {id: ship for (id, ship) in [Ship._generate(self.id) for _ in range(num_ships)]}
        self._dropoffs = {id: dropoff for (id, dropoff) in [Dropoff._generate(self.id) for _ in range(num_dropoffs)]}


class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.position = position
        self.halite_amount = halite_amount
        self.ship = None
        self.structure = None

    @property
    def is_empty(self):
        """
        :return: Whether this cell has no ships or structures
        """
        return self.ship is None and self.structure is None

    @property
    def is_occupied(self):
        """
        :return: Whether this cell has any ships
        """
        return self.ship is not None

    @property
    def has_structure(self):
        """
        :return: Whether this cell has any structures
        """
        return self.structure is not None

    @property
    def structure_type(self):
        """
        :return: What is the structure type in this cell
        """
        return None if not self.structure else type(self.structure)

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def mark_safe(self):
        self.ship = None

    def __eq__(self, other):
        return self.position == other.position

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'MapCell({}, halite={})'.format(self.position, self.halite_amount)


class GameMap:
    """
    The game map.

    Can be indexed by a position, or by a contained entity.
    Coordinates start at 0. Coordinates are normalized for you
    """
    def __init__(self, cells, width, height):
        self.width = width
        self.height = height
        self._cells = cells

    def __getitem__(self, location):
        """
        Getter for position object or entity objects within the game map
        :param location: the position or entity to access in this map
        :return: the contents housing that cell or entity
        """
        if isinstance(location, Position):
            location = self.normalize(location)
            return self._cells[location.y][location.x]
        elif isinstance(location, Entity):
            return self._cells[location.position.y][location.position.x]
        return None

    def calculate_distance(self, source, target):
        """
        Compute the Manhattan distance between two locations.
        Accounts for wrap-around.
        :param source: The source from where to calculate
        :param target: The target to where calculate
        :return: The distance between these items
        """
        resulting_position = abs(source - target)
        return min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)

    def normalize(self, position):
        """
        Normalized the position within the bounds of the toroidal map.
        i.e.: Takes a point which may or may not be within width and
        height bounds, and places it within those bounds considering
        wraparound.
        :param position: A position object.
        :return: A normalized position object fitting within the bounds of the map
        """
        return Position(position.x % self.width, position.y % self.height)

    def normalize_direction(self,direction):
        if direction.x > 1:
            direction.x = direction.x - self.width
        elif direction.x < -1:
            direction.x = direction.x + self.width

        if direction.y > 1:
            direction.y = direction.y - self.height
        elif direction.y < -1:
            direction.y = direction.y + self.height      

        return direction  

    @staticmethod
    def _get_target_direction(source, target):
        """
        Returns where in the cardinality spectrum the target is from source. e.g.: North, East; South, West; etc.
        NOTE: Ignores toroid
        :param source: The source position
        :param target: The target position
        :return: A tuple containing the target Direction. A tuple item (or both) could be None if within same coords
        """
        return (Direction.South if target.y > source.y else Direction.North if target.y < source.y else None,
                Direction.East if target.x > source.x else Direction.West if target.x < source.x else None)

    def get_safe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move mechanic does not account for collisions. The multiple directions are if both directional movements
        are viable.
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        possible_moves = []
        distance = abs(destination - source)
        y_cardinality, x_cardinality = self._get_target_direction(source, destination)

        if distance.x != 0:
            possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                  else Direction.invert(x_cardinality))
        if distance.y != 0:
            possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                  else Direction.invert(y_cardinality))
        return possible_moves

        def get_safe_positions(self, source, destination):
            """
            Return the Direction(s) to move closer to the target point, or empty if the points are the same.
            This move mechanic does not account for collisions. The multiple directions are if both directional movements
            are viable.
            :param source: The starting position
            :param destination: The destination towards which you wish to move your object.
            :return: A list of valid (closest) Directions towards your target.
            """
            possible_moves = []
            distance = abs(destination - source)
            y_cardinality, x_cardinality = self._get_target_direction(source, destination)

            if distance.x != 0:
                possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                      else Direction.invert(x_cardinality))
            if distance.y != 0:
                possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                      else Direction.invert(y_cardinality))
            return possible_moves

    def naive_navigate(self, ship, destination):
        """
        Returns a singular safe move towards the destination.

        :param ship: The ship to move.
        :param destination: Ending position
        :return: A direction.
        """
        if ship.halite_amount >= (1/constants.MOVE_COST_RATIO)*self[ship.position].halite_amount and not self[ship.position].has_structure:
            for direction in self.get_safe_moves(ship.position, destination):
                target_pos = ship.position.directional_offset(direction)
                if not self[target_pos].is_occupied:
                    self[target_pos].mark_unsafe(ship)
                    self[ship.position].mark_safe()
                    return direction

        return Direction.Still

    def aStar_navigate(self,ship,destination, end_game = False):
        if ship.halite_amount < (1/constants.MOVE_COST_RATIO)*self[ship.position].halite_amount and not self[ship.position].has_structure:
            return Direction.Still
        openset = set()
        closedset = set()
        current = (ship.position.x,ship.position.y)
        goal = (destination.x, destination.y)
        openset.add(current)
        movement_cost = {current: 0}
        hueristic_cost = {current: self.calculate_distance(ship.position,destination)}
        total_cost = {current: self.calculate_distance(ship.position,destination)}
        parent = {current: None}

        while openset:
            min_cost = min(total_cost.values())
            current = [k for k, v in total_cost.items() if v==min_cost]
            current = current[0]
            if current == goal:
                path = []
                while parent[current]:
                    path.append(current)
                    current = parent[current]
                if not path:
                    return Direction.Still
                path = path[::-1]
                target_position = Position(path[0][0],path[0][1])
                direction =  target_position - ship.position
                direction = self.normalize_direction(direction)
                self[ship.position].mark_safe()
                self[target_position].mark_unsafe(ship)
                move = (direction.x, direction.y)
                if move == None:
                    move = self.naive_navigate(ship,destination)
                return move

            openset.remove(current)
            del total_cost[current]
            closedset.add(current)
            current_position= Position(current[0],current[1])
            directions = current_position.get_surrounding_cardinals()
            for d in directions:
                d= self.normalize(d)
                if self[d].is_occupied:
                    if end_game and self[d].has_structure:
                        pass
                    else:
                        if self.calculate_distance(ship.position,d) < 2:
                            continue
                node = (d.x,d.y)
                if node in closedset:
                    continue
                if node in openset:
                    new_g = movement_cost[current] + (1/constants.MOVE_COST_RATIO)*self[current_position].halite_amount
                    if movement_cost[node] > new_g:
                        movement_cost[node] = new_g
                        total_cost[node] = movement_cost[node] + hueristic_cost[node]
                        parent[node] = current
                else:
                    movement_cost[node] = movement_cost[current] + (1/constants.MOVE_COST_RATIO)*self[current_position].halite_amount
                    hueristic_cost[node] = self.calculate_distance(d,destination)
                    total_cost[node] = movement_cost[node] + hueristic_cost[node]
                    parent[node] = current
                    openset.add(node)
        return self.naive_navigate(ship,destination)


    @staticmethod
    def _generate():
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height)

    def _update(self):
        """
        Updates this map object from the input given by the game engine
        :return: nothing
        """
        # Mark cells as safe for navigation (will re-mark unsafe cells
        # later)
        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].ship = None

        for _ in range(int(input())):
            cell_x, cell_y, cell_energy = map(int, input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy
