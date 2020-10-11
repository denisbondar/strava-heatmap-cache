from flask import Flask, make_response, Response
from main import Cache, Tile, StravaFetcher, cache_dir, auth_data


app = Flask(__name__)
cache = Cache(cache_dir)
fetcher = StravaFetcher(auth_data, cache)


@app.route('/<int:z>/<int:x>/<int:y>.png')
def get_tile(x, y, z):
    if z < 7 or z > 16:
        return Response(status=404)

    tile = Tile(x, y, z)
    if not cache.tile_already_in_cache(tile):
        fetcher.fetch([tile])
    content = cache.read(tile)

    response = make_response(content)
    response.headers.set('Content-Type', 'image/png')
    response.headers.set(
        'Content-Disposition', 'inline', filename='%s.png' % y)
    response.headers.set('Content-Length', len(content))
    response.headers.set('Cache-Control', 'max-age=%d' % (60*60*24*30))
    return response


if __name__ == '__main__':
    app.run()
