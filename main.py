import asyncio
import math
import os
from collections import namedtuple
from random import choice
from typing import List

import aiofiles
import aiohttp

CloudFrontAuth = namedtuple("CloudFrontAuth", "key_pair_id signature policy")
GeoPoint = namedtuple("GeoPoint", "latitude longitude")
script_abs_dir = os.path.abspath(os.path.dirname(__file__))


class Tile:
    def __init__(self, x: int, y: int, z: int) -> None:
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def create_from_geo_coordinates(cls,
                                    point: GeoPoint,
                                    zoom: int):
        """
        >>> Tile.create_from_geo_coordinates(GeoPoint(46.90946, 30.19284), 9)
        Tile(298, 180, 9)
        """
        x, y = cls.geo_to_tile(point, zoom)
        return cls(x, y, zoom)

    @staticmethod
    def geo_to_tile(point: GeoPoint, zoom):
        """
        >>> Tile.geo_to_tile(GeoPoint(46.90946, 30.19284), 9)
        (298, 180)
        >>> Tile.geo_to_tile(GeoPoint(46.10655, 31.39070), 9)
        (300, 181)
        """
        lat_rad = math.radians(point.latitude)
        n = 2.0 ** zoom
        x = int((point.longitude + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    @classmethod
    def generate_from_area(cls,
                           geo_coordinates_1: GeoPoint,
                           geo_coordinates_2: GeoPoint,
                           zoom_min: int,
                           zoom_max: int):
        """
        >>> gen = Tile.generate_from_area(GeoPoint(46.90946, 30.19284), GeoPoint(46.10655, 31.39070), 9, 9)
        >>> [t for t in gen]
        [Tile(298, 180, 9), Tile(299, 180, 9), Tile(300, 180, 9), Tile(298, 181, 9), Tile(299, 181, 9), Tile(300, 181, 9)]
        """
        apex = GeoPoint(max(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
                        min(geo_coordinates_1.longitude, geo_coordinates_2.longitude))
        vertex = GeoPoint(min(geo_coordinates_1.latitude, geo_coordinates_2.latitude),
                          max(geo_coordinates_1.longitude, geo_coordinates_2.longitude))

        for z in range(zoom_min, zoom_max + 1):
            first_tile_x, first_tile_y = cls.geo_to_tile(apex, z)
            last_tile_x, last_tile_y = cls.geo_to_tile(vertex, z)
            for y in range(first_tile_y, last_tile_y + 1):
                for x in range(first_tile_x, last_tile_x + 1):
                    yield Tile(x, y, z)

    @property
    def relative_file_path(self):
        return f"{self.z}/{self.x}/{self.y}.png.tile"

    def __repr__(self) -> str:
        return f"Tile({self.x}, {self.y}, {self.z})"


Tiles = List[Tile]


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
        return os.path.join(self.cache_abs_path, tile.relative_file_path)


class StravaFetcher:
    free_tile_zoom = 11
    url_auth = "https://heatmap-external-{server}.strava.com/tiles-auth/{activity}/{color}/{z}/{x}/{y}.png"
    url_free = "https://heatmap-external-{server}.strava.com/tiles/{activity}/{color}/{z}/{x}/{y}.png"
    semaphore_value = 5

    def __init__(self,
                 auth: CloudFrontAuth,
                 cache: Cache,
                 activity='ride',
                 color='bluered') -> None:
        self.auth = auth
        self.cache = cache
        self.activity = activity
        self.color = color

    def fetch(self, tiles: Tiles):
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
        return tile.z <= self.free_tile_zoom

    async def task_queue(self, tiles: Tiles):
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
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    content = await response.read()
                    await self.cache.write(tile, content)
                # todo тут бы надо отдавать контент на обработку чтобы узнать что конкретно за ошибка
                elif response.status == 403:
                    raise PermissionError("[403] STRAVA Access denied. " + await response.text())


class CacheWarmer:
    def __init__(self, cache: Cache, strava_fetcher: StravaFetcher) -> None:
        self.cache = cache
        self.strava_fetcher = strava_fetcher

    def warm_up(self,
                geo_coordinates_1: GeoPoint,
                geo_coordinates_2: GeoPoint,
                zoom_min: int,
                zoom_max: int,
                max_tiles=None):
        tiles = []
        for tile in Tile.generate_from_area(geo_coordinates_1, geo_coordinates_2, zoom_min, zoom_max):
            if not self.cache.tile_already_in_cache(tile):
                tiles.append(tile)
                if max_tiles and len(tiles) >= max_tiles:
                    break
        print("Count tiles to load:", len(tiles))
        self.strava_fetcher.fetch(tiles)


if __name__ == '__main__':
    auth_data = CloudFrontAuth(os.getenv('KEY-PAIR-ID'),
                               os.getenv('SIGNATURE'),
                               os.getenv('POLICY'))
    cache = Cache(os.path.join(script_abs_dir, os.getenv('CACHE_DIR')))
    strava_fetcher = StravaFetcher(auth_data, cache)
    warmer = CacheWarmer(cache, strava_fetcher)

    warmer.warm_up(GeoPoint(46.90946, 30.19284),
                   GeoPoint(46.10655, 31.39070),
                   7, 15, max_tiles=1000)
