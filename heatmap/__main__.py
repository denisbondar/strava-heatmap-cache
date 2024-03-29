from aiohttp import web

from heatmap.strava import cache
from heatmap.tile import Tile

routes = web.RouteTableDef()


@routes.get(r"/{z:\d+}/{x:\d+}/{y:\d+}.png")
async def get_tile(request: web.Request) -> web.StreamResponse:
    z = int(request.match_info["z"])
    x = int(request.match_info["x"])
    y = int(request.match_info["y"])

    if z < 7 or z > 16:
        return web.Response(status=404, reason="Zoom is out of range")

    tile = Tile(x, y, z)
    if not cache.is_tile_already_in_cache(tile):
        return web.Response(status=404, reason="Not in cache")

    return web.FileResponse(path=cache.path_for_tile_file(tile))


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8080)
