import logging

MAX_FLIGHT_DIST = 10


def solve(stations: list[int], target: int) -> int:
    cargo_pos: int = 0
    person_pos: int = 0
    total_walked: int = 0

    # Include target in the list of points to evaluate
    stations = stations + [target]

    def nearest_station() -> int:
        """
        Returns the next nearest station ahead of the cargo.
        Target is included as a "station" to evaluate.
        O(n)
        """
        nonlocal stations, cargo_pos
        return min(
            (s for s in stations if s > cargo_pos), key=lambda s: abs(s - cargo_pos)
        )

    def fly(station: int) -> bool:
        """
        Flies to the station if it is within flight range,
        otherwise to the max flight distance.

        Returns True if at a next station
        or False otherwise
        """
        logging.info("Flying...")
        nonlocal cargo_pos
        if (station - cargo_pos) <= MAX_FLIGHT_DIST:
            cargo_pos = station
            return True

        cargo_pos += MAX_FLIGHT_DIST
        return False

    def walk(station: int):
        """
        Walks to the next station neareset the cargo.
        """
        nonlocal cargo_pos, person_pos, total_walked
        logging.info(f"Walking from {person_pos} to {station}")
        steps = station - person_pos
        person_pos += steps
        total_walked += steps
        cargo_pos = person_pos
        logging.info(f"Walked a total of {total_walked} steps")
        logging.info(f"Current cargo position is {cargo_pos}")

    logging.info("Starting...")
    logging.info(f"Stations: {stations}")
    # inital step
    # Find nearest station to walk to
    nearest = min(stations)
    walk(nearest)

    while cargo_pos < target:
        logging.info(f"Cargo at: {cargo_pos}")
        # Find nearest station
        nearest = nearest_station()
        logging.info(f"Nearest station is at {nearest}")
        at_station = fly(nearest)

        if at_station:
            # Continue to fly again
            continue

        next_station = nearest_station()
        walk(next_station)

    logging.info(f"Cargo delivered: {cargo_pos}")
    return total_walked
