import pytest
import numpy as np
import pandas as pd
import re
from unittest.mock import patch
from core import dttms
from core.monitoring.services_widget import ServicesWidget


@pytest.fixture
def service_widget() -> ServicesWidget:
    return ServicesWidget()


@pytest.fixture
def verbose_data() -> pd.DataFrame:
    dtm_now = dttms.now()
    dtm_min_ago = dttms.now() - np.timedelta64(1, "m")
    dtm_stale = dttms.now() - np.timedelta64(1, "h")
    dtm_really_stale = dttms.now() - np.timedelta64(4, "D")
    records = [
        {"dttm": dtm_now, "name": "service1", "running": 0, "connected": 0},
        {"dttm": dtm_now, "name": "service2", "running": 1, "connected": 1},
        {"dttm": dtm_now, "name": "service3", "running": 1, "connected": 0},
        {"dttm": dtm_now, "name": "service4", "running": 1, "connected": 0},
        {"dttm": dtm_min_ago, "name": "service1", "running": 1, "connected": 1},
        {"dttm": dtm_min_ago, "name": "service2", "running": 1, "connected": 0},
        {"dttm": dtm_min_ago, "name": "service3", "running": 1, "connected": 1},
        {"dttm": dtm_min_ago, "name": "service4", "running": 0, "connected": 0},
        {"dttm": dtm_stale, "name": "service4", "running": 1, "connected": 0},
        {"dttm": dtm_stale, "name": "service5", "running": 1, "connected": 1},
        {"dttm": dtm_really_stale, "name": "service4", "running": 1, "connected": 1},
        {"dttm": dtm_really_stale, "name": "service6", "running": 0, "connected": 1},
    ]
    return pd.DataFrame.from_records(records).sort_values("dttm", ascending=False)


@pytest.fixture
def non_verbose_data(verbose_data: pd.DataFrame) -> pd.DataFrame:
    df = verbose_data.sort_values(by=["dttm"], ascending=False)
    df.drop_duplicates(subset=["name"], keep="first", inplace=True)
    return df


@pytest.fixture
def mocked_query(verbose_data, non_verbose_data):
    def _mocked_query(query, *args, **kwargs):
        date_pattern = r"between\s+'([^']+)' and '([^']+)'"
        matches = re.search(date_pattern, query)
        date_1, date_2 = matches.groups()
        date_1, date_2 = dttms.as_dttm(date_1), dttms.as_dttm(date_2)
        data = non_verbose_data if "ROW_NUMBER()" in query else verbose_data
        data = data.loc[data["dttm"].between(date_1, date_2)]

        name_pattern = r"name\s*=\s*'([^']*)'"
        matches = re.search(name_pattern, query)
        if matches:
            (name,) = matches.groups()
            data = data.loc[data["name"] == name]
        return data

    return _mocked_query


@patch("core.dbs.Database.query")
def test_status_errs(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(errs=True)
    result_stale = result.loc[result["is_stale"]]
    services = set(result["name"].values)
    services_stale = set(result_stale["name"].values)

    assert len(result) == 4
    assert len(result_stale) == 1
    assert services == {"service1", "service3", "service4", "service5"}
    assert services_stale == {"service5"}


@patch("core.dbs.Database.query")
def test_status_errs_verbose(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(errs=True, verbose=True)
    result_stale = result.loc[result["is_stale"]]

    res_count = result.groupby("name")["running"].count()
    stale_count = result_stale.groupby("name")["running"].count()

    assert len(result) == 7
    assert res_count["service1"] == 1
    assert res_count["service2"] == 1
    assert res_count["service3"] == 1
    assert res_count["service4"] == 3
    assert res_count["service5"] == 1

    assert len(result_stale) == 2
    assert stale_count["service4"] == 1
    assert stale_count["service5"] == 1


@patch("core.dbs.Database.query")
def test_status_with_name_filter(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(name="service1")

    assert len(result) == 1
    assert (result["name"] == "service1").all()


@patch("core.dbs.Database.query")
def test_status_with_name_filter_verbose(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(name="service4", verbose=True)
    result_stale = result.loc[result["is_stale"]]

    res_count = result.groupby("name")["running"].count()
    stale_count = result_stale.groupby("name")["running"].count()

    assert len(result) == 3
    assert res_count["service4"] == 3

    assert len(result_stale) == 1
    assert stale_count["service4"] == 1


@patch("core.dbs.Database.query")
def test_status_verbose(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(verbose=True)
    result_stale = result.loc[result["is_stale"]]

    res_count = result.groupby("name")["running"].count()
    stale_count = result_stale.groupby("name")["running"].count()

    assert len(result) == 10
    assert res_count["service1"] == 2
    assert res_count["service2"] == 2
    assert res_count["service3"] == 2
    assert res_count["service4"] == 3
    assert res_count["service5"] == 1

    assert len(result_stale) == 2
    assert stale_count["service4"] == 1
    assert stale_count["service5"] == 1


@patch("core.dbs.Database.query")
def test_status_verbose_large_time_span(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(verbose=True, from_dttm="now-10d")
    result_stale = result.loc[result["is_stale"]]

    res_count = result.groupby("name")["running"].count()
    stale_count = result_stale.groupby("name")["running"].count()

    assert len(result) == 12
    assert res_count["service1"] == 2
    assert res_count["service2"] == 2
    assert res_count["service3"] == 2
    assert res_count["service4"] == 4
    assert res_count["service5"] == 1
    assert res_count["service6"] == 1

    assert len(result_stale) == 4
    assert stale_count["service4"] == 2
    assert stale_count["service5"] == 1
    assert stale_count["service6"] == 1


@patch("core.dbs.Database.query")
def test_status_default(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status()
    result_stale = result.loc[result["is_stale"]]
    result_error = result.loc[result["is_error"]]

    res_count = result.groupby("name")["running"].count()
    stale_count = result_stale.groupby("name")["running"].count()
    error_count = result_error.groupby("name")["running"].count()

    assert len(result) == 5
    assert res_count["service1"] == 1
    assert res_count["service2"] == 1
    assert res_count["service3"] == 1
    assert res_count["service4"] == 1
    assert res_count["service5"] == 1

    assert len(result_stale) == 1
    assert stale_count["service5"] == 1

    assert len(result_error) == 4
    assert error_count["service1"] == 1
    assert error_count["service3"] == 1
    assert error_count["service4"] == 1
    assert error_count["service5"] == 1


@patch("core.dbs.Database.query")
def test_status_no_stale_cutoff(mock_query, mocked_query, service_widget):
    mock_query.side_effect = mocked_query
    result = service_widget.status(stale_cutoff=None)
    result_error = result.loc[result["is_error"]]

    res_count = result.groupby("name")["running"].count()
    error_count = result_error.groupby("name")["running"].count()

    assert len(result) == 5
    assert res_count["service1"] == 1
    assert res_count["service2"] == 1
    assert res_count["service3"] == 1
    assert res_count["service4"] == 1
    assert res_count["service5"] == 1

    assert len(result_error) == 3
    assert error_count["service1"] == 1
    assert error_count["service3"] == 1
    assert error_count["service4"] == 1
