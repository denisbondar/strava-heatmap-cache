from time import time

from heatmap.config_reader import config
from heatmap.logger import logger
from heatmap.strava import cache_warmer
from heatmap.tile import GeoPoint


def main():
    apex = GeoPoint(*(float(n.strip()) for n in config.area.apex.split(",")))
    vertex = GeoPoint(*(float(n.strip()) for n in config.area.vertex.split(",")))
    start_time = time()
    logger.info("Start building cache.")
    try:
        cache_warmer.warm_up(apex, vertex, range(7, 17), max_tiles=8000)
    except PermissionError as e:
        logger.error(e)
    logger.info(f"Spent in {round((time() - start_time), 2)} seconds.")


if __name__ == "__main__":
    main()
