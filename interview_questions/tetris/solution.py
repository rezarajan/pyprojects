type Grid = list[list[int]]
type Point = tuple[int, int]


class OccupancyGrid:
    def __init__(self, w: int, h: int):
        self.grid: Grid = [[0 for _ in range(w)] for _ in range(h)]
        self.height = h
        self.width = w

    def get_height(self):
        return self.height

    def get_width(self):
        return self.width

    def get_point(self, point: Point) -> int:
        """
        Returns the value of the grid at the specified point
        """
        return self.grid[point[0]][point[1]]

    def is_occupied(self, point: Point) -> bool:
        """
        Returns the occupancy status of the grid
        at the specified point.
        """
        return bool(self.get_point(point))

    def get_top(self, col) -> int:
        """
        Returns the index of the first occupied row
        at a specified column.

        If completely unoccupied, returns the grid height.
        """
        # O(n) worst case
        for i in range(self.get_height()):
            point = (i, col)
            if self.get_point(point):
                return i

        return self.get_height()

    def get_tip(self, col) -> int:
        """
        Returns the index of the last occupied row
        in the grid at the specified column.

        Returns 0 if completely unoccupied.
        """
        for i in range(self.get_height(), 0, -1):
            point = (i, col)
            if self.get_point(point):
                return i

        return 0

    def get_base(self) -> Point:
        """
        Returns the first occupied point of the lowest row
        with at least one occupancy.

        Returns (0,0) if completely unoccupied.
        """
        # O(n^2)
        for i in range(self.get_height()):
            for j in range(self.get_width()):
                point = (i, j)
                if self.get_point(point) == 0:
                    continue
                return point
        return (0, 0)


class Tetris:
    def __init__(self, field: OccupancyGrid):
        self.field: OccupancyGrid = field

    def update_field(self, figure: OccupancyGrid, index: int):
        """
        Updates the field with the provided figure, inserted
        at the left-aligned index.
        """
        pass

    def check_collisions(self, figure: OccupancyGrid, index: int):
        """
        Checks for collisons of a figure applied to the field at the
        left-aligned index.
        """
        # Check for out-of-bounds
        # O(1)
        if self.field.get_width() < (index + figure.get_width()):
            raise OverflowError("Figure out of bounds")

        # Check for collision
        # The rule is that the tip of the figure must
        # reach the max depth. From there we can check
        # collisions on other points.

        # Get the base of the figure
        # Project the base to the field to find the endpoint
        # Check for collisions using the projected point as a pivot
        fig_base = figure.get_base()
        offset_tip = index + fig_base[1]
        projected_tip = self.field.get_tip(offset_tip)
        projected_base = (projected_tip, offset_tip)

        # TODO:

    def search(self, figure: OccupancyGrid) -> list[int]:
        """
        Searches for valid placement indices for the provided
        figure, in the field.
        """
        # TODO:
        return []


def main():
    pass


if __name__ == "__main__":
    main()
