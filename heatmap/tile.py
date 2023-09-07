import dataclasses
import math

EMPTY_TILE = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x01\x03\x00\x00\x00f\xbc:%"
    b"\x00\x00\x00\x03PLTE\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\x1f"
    b"IDATh\xde\xed\xc1\x01\r\x00\x00\x00\xc2 \xfb\xa76\xc77`\x00\x00\x00\x00\x00\x00\x00\x00q\x07!\x00"
    b"\x00\x01\xa7W)\xd7\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclasses.dataclass
class GeoPoint:
    latitude: float
    longitude: float


class Tile:
    def __init__(self, x: int, y: int, z: int) -> None:
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def create_from_geo_coordinates(cls, point: GeoPoint, zoom: int):
        x, y = cls.geo_to_tile(point, zoom)
        return cls(x, y, zoom)

    @staticmethod
    def geo_to_tile(point: GeoPoint, zoom):
        lat_rad = math.radians(point.latitude)
        n = 2.0**zoom
        x = int((point.longitude + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    @classmethod
    def generate_from_area(cls, geo_coordinates_1: GeoPoint, geo_coordinates_2: GeoPoint, zoom_range):
        apex = GeoPoint(
            max(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
            min(geo_coordinates_1.longitude, geo_coordinates_2.longitude),
        )
        vertex = GeoPoint(
            min(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
            max(geo_coordinates_1.longitude, geo_coordinates_2.longitude),
        )

        for z in zoom_range:
            first_tile_x, first_tile_y = cls.geo_to_tile(apex, z)
            last_tile_x, last_tile_y = cls.geo_to_tile(vertex, z)
            for y in range(first_tile_y, last_tile_y + 1):
                for x in range(first_tile_x, last_tile_x + 1):
                    yield Tile(x, y, z)

    def __repr__(self) -> str:
        return f"Tile({self.x}, {self.y}, {self.z})"

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z
