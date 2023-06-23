import asyncio
import logging
import math
import os
from collections import namedtuple
from random import choice
from time import time

import aiofiles
import aiohttp
from aiohttp import client_exceptions

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CloudFrontAuth = namedtuple("CloudFrontAuth", "key_pair_id signature policy")
GeoPoint = namedtuple("GeoPoint", "latitude longitude")
script_abs_dir = os.path.abspath(os.path.dirname(__file__))
cache_dir = os.path.join(script_abs_dir, 'cache')

auth_data = CloudFrontAuth(os.getenv('KEY_PAIR_ID'),
                           os.getenv('SIGNATURE'),
                           os.getenv('POLICY'))

point_1_x, point_1_y = os.getenv('AREA_APEX', '46.90946, 30.19284').split(',')
point_2_x, point_2_y = os.getenv('AREA_VERTEX', '46.10655, 31.39070').split(',')

EMPTY_TILE = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x01\x03\x00\x00\x00f\xbc:%" \
             b"\x00\x00\x00\x03PLTE\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00@\xe6\xd8f\x00\x00\x00\x1f" \
             b"IDATh\xde\xed\xc1\x01\r\x00\x00\x00\xc2 \xfb\xa76\xc77`\x00\x00\x00\x00\x00\x00\x00\x00q\x07!\x00" \
             b"\x00\x01\xa7W)\xd7\x00\x00\x00\x00IEND\xaeB`\x82"


class Tile:
    def __init__(self, x: int, y: int, z: int) -> None:
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def create_from_geo_coordinates(cls,
                                    point: GeoPoint,
                                    zoom: int):
        x, y = cls.geo_to_tile(point, zoom)
        return cls(x, y, zoom)

    @staticmethod
    def geo_to_tile(point: GeoPoint, zoom):
        lat_rad = math.radians(point.latitude)
        n = 2.0 ** zoom
        x = int((point.longitude + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    @classmethod
    def generate_from_area(cls,
                           geo_coordinates_1: GeoPoint,
                           geo_coordinates_2: GeoPoint,
                           zoom_range):
        apex = GeoPoint(max(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
                        min(geo_coordinates_1.longitude, geo_coordinates_2.longitude))
        vertex = GeoPoint(min(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
                          max(geo_coordinates_1.longitude, geo_coordinates_2.longitude))

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


def filename_for_file(tile: Tile) -> str:
    return f"{tile.z}/{tile.x}/{tile.y}png.tile"


class Cache:
    def __init__(self, cache_abs_path: str) -> None:
        self.cache_abs_path = cache_abs_path

    def read(self, tile: Tile):
        with open(self.abs_tile_path(tile), "rb") as file:
            return file.read()

    async def write(self, tile: Tile, content: bytes):
        self.mkdir(tile)
        async with aiofiles.open(self.abs_tile_path(tile), "wb") as file:
            await file.write(content)

    def tile_already_in_cache(self, tile: Tile) -> bool:
        return os.path.isfile(self.abs_tile_path(tile))

    def mkdir(self, tile: Tile):
        path = '/'.join(self.abs_tile_path(tile).split('/')[:-1])
        if not os.path.exists(path):
            os.makedirs(path)

    def abs_tile_path(self, tile):
        return os.path.join(self.cache_abs_path, filename_for_file(tile))


class StravaFetcher:
    free_tile_max_zoom = 11
    url_auth = "https://heatmap-external-{server}.strava.com/tiles-auth/{activity}/{color}/{z}/{x}/{y}.png"
    url_free = "https://heatmap-external-{server}.strava.com/tiles/{activity}/{color}/{z}/{x}/{y}.png"
    semaphore_value = 10

    def __init__(self,
                 auth: CloudFrontAuth,
                 cache: Cache,
                 activity='ride',
                 color='bluered') -> None:
        self.auth = auth
        self.cache = cache
        self.activity = activity
        self.color = color

    def fetch(self, tiles: list[Tile]):
        asyncio.run(self.task_queue(tiles))

    def __url(self, tile) -> str:
        if self.__tile_is_free(tile):
            url = self.url_free
        else:
            url = self.url_auth
        server = choice(('a', 'b', 'c',))
        return url.format(server=server,
                          activity=self.activity,
                          color=self.color,
                          x=tile.x, y=tile.y, z=tile.z)

    def __url_params(self, tile: Tile):
        params = {"px": "256",
                  "v": "19"}
        if not self.__tile_is_free(tile):
            params.update({"Key-Pair-Id": self.auth.key_pair_id,
                           "Signature": self.auth.signature,
                           "Policy": self.auth.policy})
        return params

    def __tile_is_free(self, tile: Tile):
        return tile.z <= self.free_tile_max_zoom

    async def task_queue(self, tiles: list[Tile]):
        tasks = []
        for tile in tiles:
            tasks.append(asyncio.create_task(self.download_tile(tile)))
        semaphore = asyncio.Semaphore(self.semaphore_value)
        async with semaphore:
            return await asyncio.gather(*tasks)

    async def download_tile(self, tile: Tile):
        url = self.__url(tile)
        params = self.__url_params(tile)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        content = await response.read()
                        await self.cache.write(tile, content)
                    elif response.status == 404:
                        await self.cache.write(tile, EMPTY_TILE)
                    else:
                        logger.warning(
                            f"For {tile} received an unexpected status code {response.status}: {await response.text()}"
                        )
            except client_exceptions.ServerDisconnectedError as e:
                raise PermissionError("It is necessary to lower the value of the semaphore. %s" % e) from e
            except client_exceptions.ClientOSError as e:
                raise PermissionError("%s" % e) from e


class CacheWarmer:
    def __init__(self, cache: Cache, strava_fetcher: StravaFetcher) -> None:
        self.cache = cache
        self.strava_fetcher = strava_fetcher

    def warm_up(self,
                geo_coordinates_1: GeoPoint,
                geo_coordinates_2: GeoPoint,
                zoom_range,
                max_tiles=None):
        tiles = []
        for tile in Tile.generate_from_area(geo_coordinates_1, geo_coordinates_2, zoom_range):
            if not self.cache.tile_already_in_cache(tile):
                tiles.append(tile)
                if max_tiles and len(tiles) >= max_tiles:
                    break
        if not tiles:
            logger.info("There are no tiles to load")
        else:
            self.strava_fetcher.fetch(tiles)


if __name__ == '__main__':
    cache = Cache(cache_dir)
    strava_fetcher = StravaFetcher(auth_data, cache)
    warmer = CacheWarmer(cache, strava_fetcher)

    start_time = time()
    logger.info("Start building cache.")
    try:
        warmer.warm_up(GeoPoint(float(point_1_x.strip()), float(point_1_y.strip())),
                       GeoPoint(float(point_2_x.strip()), float(point_2_y.strip())),
                       range(7, 17),
                       max_tiles=8000)
    except PermissionError as e:
        logger.error(e)
    logger.info(f"Spent in {round((time() - start_time), 2)} seconds.")
