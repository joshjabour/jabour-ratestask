from flask import Flask, request, jsonify, Response
import datetime
import os
import psycopg2
import json

app = Flask(__name__)

@app.route('/rates', methods=['GET']) 
def get_price_averages():
    # Retrieve query parameters
    date_from = request.args.get('date_from') # for testing, use '2016-01-01'
    date_to = request.args.get('date_to') # for testing, use '2016-01-05'
    origin = request.args.get('origin') # for testing, use 'CNSGH' (or 'china_main')
    destination = request.args.get('destination') # for testing, use 'north_europe_main' (or 'NLRTM')
    
    # Check if date_from, date_to, origin, and destination are not empty
    if not date_from or not date_to or not origin or not destination:
        return jsonify({'Error': 'Missing query parameters'}), 400
    # Check if date_from and date_to are in the correct format
    try:
        datetime.datetime.strptime(date_from, '%Y-%m-%d')
        datetime.datetime.strptime(date_to, '%Y-%m-%d')
    except ValueError:
        return jsonify({'Error': 'Invalid date format'}), 400

    originPortCodes = []
    destinationPortCodes = []
    prices = []
    
    connection = None
    cursor = None

    try:
        connection = psycopg2.connect(
            host=os.environ['POSTGRES_DB_HOST'],
            database=os.environ['POSTGRES_DB_NAME'],
            user=os.environ['POSTGRES_USERNAME'],
            password=os.environ['POSTGRES_PASSWORD'])

        # Get the port codes for the origin and destination
        # First, determine whether the a port code or a region slug was supplied for the origin and destination
        # ASSUMPTION: I've defined a port code as an upper-case string with 5 or fewer characters
        if len(origin) <= 5 and origin.isupper(): # Port code was given
            originPortCodes.append(origin)
        else: # Region slug was given. Get the port codes for the region and descendants
            originPortCodes = get_port_codes(origin, connection)
        if len(destination) <= 5 and destination.isupper(): # Port code was given
            destinationPortCodes.append(destination) 
        else: # Region slug was given. Get the port codes for the region and descendants
            destinationPortCodes = get_port_codes(destination, connection)

        # Get price averages across all ports for each day in the range supplied
        cursor = connection.cursor()
        cursor.execute('''
            -- Generate a series of every day between date_from and date_to 
            -- so that the results will include all days in the range even if
            -- there are no records for a particular day in the prices table
            WITH days AS (
                SELECT GENERATE_SERIES(%s, %s, interval '1 day')::date AS day
            )
            -- Get the average price for each day in the range having at least 3
            -- records, rounded to the nearest whole number
            SELECT
                days.day,
                CASE
                    WHEN COUNT(*) >= 3 THEN ROUND(AVG(price))
                ELSE NULL
                END AS average_price
            FROM
                days
                LEFT JOIN prices ON 
                    days.day = prices.day AND
                    orig_code IN %s AND
                    dest_code IN %s
            GROUP BY days.day
            ORDER BY days.day;
            ''', (date_from, date_to, tuple(originPortCodes), tuple(destinationPortCodes)))
        prices = cursor.fetchall()
        cursor.close()

    except psycopg2.Error as error:
        app.logger.error("Error fetching prices from the database: %s", error)
        return jsonify({'Error': 'Failed to fetch prices from the database. Please try again later.'}), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    
    # Convert prices to the desired JSON format
    prices_json = [
        {'day': row[0].strftime('%Y-%m-%d'), 'average_price': int(row[1]) if row[1] is not None else None}
        for row in prices
    ]

    # Use json.dumps to convert the dictionary to a JSON string
    # Set sort_keys to False (the default, but explicitly marked here for clarity) to keep the order of
    # keys in the response JSON # in the same order as required based on the task details.
    # NOTE: The order the order of keys in the response does not impact the 
    # functionality for API consumers, but this explicit ordering is for ease of testing the output
    response_json = json.dumps(prices_json, sort_keys=False)
    
    # Create a Flask Response object and set the content type to 'application/json'
    return Response(response_json, content_type='application/json; charset=utf-8')

# Retrieves the port codes for a given region slug and descendants.
# It uses a recursive query to traverse the region hierarchy.
# The function takes two parameters: the region slug and the database connection object.
# It returns a list of port codes associated with the given region.
def get_port_codes(region_slug, connection):
    cursor = None
    port_codes = []
    cursor = connection.cursor()
    cursor.execute('''
        WITH RECURSIVE region_tree AS (
            SELECT slug, parent_slug
            FROM regions
            WHERE slug = %s

            UNION ALL

            SELECT regions.slug, regions.parent_slug
            FROM regions
            JOIN region_tree ON regions.parent_slug = region_tree.slug
        )
        SELECT ports.code
        FROM ports 
        INNER JOIN region_tree ON ports.parent_slug = region_tree.slug;
        ''', (region_slug,))
    port_codes = cursor.fetchall()
    cursor.close()
    return port_codes

if __name__ == "__main__":
    app.run(debug=True)