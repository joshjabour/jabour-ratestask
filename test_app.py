import pytest
from app import app as flask_app

@pytest.fixture
def app():
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_price_averages_missing_params(client):
    response = client.get('/rates')
    assert response.status_code == 400
    assert 'Missing query parameters' in response.json['Error']

def test_get_price_averages_invalid_date_format(client):
    response = client.get('/rates?date_from=invalid&date_to=invalid&origin=CNSGH&destination=north_europe_main')
    assert response.status_code == 400
    assert 'Invalid date format' in response.json['Error']

def test_get_price_averages_invalid_date_range(client):
	response = client.get('/rates?date_from=2016-01-10&date_to=2016-01-01&origin=CNSGH&destination=north_europe_main')
	assert response.status_code == 400
	assert 'Invalid date range' in response.json['Error']

# TODO: Create additional tests here mocking the database. Since I have run out of time I will skip this part.