from core.dbs import sql_tree_filter


def test_sql_tree_filter():
    f = sql_tree_filter(["BOND:RX1", "FX:EURUSD"], ["mstrat", "asset"])
    assert f == "(mstrat='BOND' and asset='RX1') or (mstrat='FX' and asset='EURUSD')"

    f = sql_tree_filter(["BOND", "EQ", "FX:USDCAD"], ["mstrat", "asset"])
    assert f == "mstrat in ('BOND','EQ') or (mstrat='FX' and asset='USDCAD')"
