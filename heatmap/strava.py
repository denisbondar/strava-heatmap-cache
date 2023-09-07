import asyncio
from pathlib import Path
from random import choice

import aiofiles
import aiohttp
from aiohttp import client_exceptions

from heatmap.config_reader import config
from heatmap.logger import logger
from heatmap.tile import EMPTY_TILE, GeoPoint, Tile


class Cache:
    def read(self, tile: Tile):
        with open(self.path_for_tile_file(tile), "rb") as file:
            return file.read()

    async def write(self, tile: Tile, content: bytes):
        self.path_for_tile_file(tile).parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.path_for_tile_file(tile), "wb") as file:
            await file.write(content)

    def is_tile_already_in_cache(self, tile: Tile) -> bool:
        return self.path_for_tile_file(tile).is_file()

    @staticmethod
    def path_for_tile_file(tile) -> Path:
        return Path(config.cache_dir, f"{tile.z}/{tile.x}/{tile.y}png.tile").resolve().absolute()


class StravaFetcher:
    free_tile_max_zoom = 11
    url_auth = "https://heatmap-external-{server}.strava.com/tiles-auth/{activity}/{color}/{z}/{x}/{y}.png"
    url_free = "https://heatmap-external-{server}.strava.com/tiles/{activity}/{color}/{z}/{x}/{y}.png"
    semaphore_value = 10

    def __init__(self, cache: Cache, activity="ride", color="bluered") -> None:
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
        server = choice(
            (
                "a",
                "b",
                "c",
            )
        )
        return url.format(server=server, activity=self.activity, color=self.color, x=tile.x, y=tile.y, z=tile.z)

    def __url_params(self, tile: Tile):
        params = {"px": "256", "v": "19"}
        if not self.__tile_is_free(tile):
            params.update(
                {
                    "Key-Pair-Id": config.cloud_front.key_pair_id,
                    "Signature": config.cloud_front.signature.get_secret_value(),
                    "Policy": config.cloud_front.policy.get_secret_value(),
                }
            )
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

    def warm_up(self, geo_coordinates_1: GeoPoint, geo_coordinates_2: GeoPoint, zoom_range, max_tiles=None):
        tiles = []
        for tile in Tile.generate_from_area(geo_coordinates_1, geo_coordinates_2, zoom_range):
            if not self.cache.is_tile_already_in_cache(tile):
                tiles.append(tile)
                if max_tiles and len(tiles) >= max_tiles:
                    break
        if not tiles:
            logger.info("There are no tiles to load")
        else:
            self.strava_fetcher.fetch(tiles)


cache = Cache()
strava_fetcher = StravaFetcher(cache)
cache_warmer = CacheWarmer(cache, strava_fetcher)
