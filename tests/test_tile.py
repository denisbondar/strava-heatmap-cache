from main import Tile, GeoPoint


def test_create_from_geo_coordinates():
    assert Tile.create_from_geo_coordinates(GeoPoint(46.90946, 30.19284), 9) == Tile(298, 180, 9)


def test_geo_to_tile():
    assert Tile.geo_to_tile(GeoPoint(46.90946, 30.19284), 9) == (298, 180)
    assert Tile.geo_to_tile(GeoPoint(46.10655, 31.39070), 9) == (300, 181)


def test_generate_from_area():
    gen = Tile.generate_from_area(GeoPoint(46.90946, 30.19284),
                                  GeoPoint(46.10655, 31.39070),
                                  range(9, 10))
    assert [t for t in gen] == [Tile(298, 180, 9), Tile(299, 180, 9),
                                Tile(300, 180, 9), Tile(298, 181, 9),
                                Tile(299, 181, 9), Tile(300, 181, 9)]
