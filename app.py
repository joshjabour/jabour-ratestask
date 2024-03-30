from flask import Flask, request, jsonify, Response
import datetime
import os
import psycopg2
import json

app = Flask(__name__)

@app.route('/rates', methods=['GET']) 
def get_price_averages():
    # Retrieve query parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    
    # Check if date_from, date_to, origin, and destination are not empty
    if not date_from or not date_to or not origin or not destination:
        return jsonify({'Error': 'Missing query parameters'}), 400
    # Check if date_from and date_to are in the correct format
    try:
        datetime.datetime.strptime(date_from, '%Y-%m-%d')
        datetime.datetime.strptime(date_to, '%Y-%m-%d')
    except ValueError:
        return jsonify({'Error': 'Invalid date format'}), 400
    # Check if date_from is earlier than date_to
    if date_from >= date_to:
        return jsonify({'Error': 'Invalid date range. The date_from must be earlier than the date_to'}), 400

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
        # Since we're dealing with UN/LOCODEs I defined a port code as an alphanumeric upper-case string with 5 
        # or fewer characters
        
        # For origin:
        if len(origin) <= 5 and origin.isupper():  # Port code was given
            if not port_code_exists(origin, connection):
                app.logger.error(f"Port {origin} does not exist.")
                return jsonify({"Error": f"Port {origin} does not exist."}), 400
            originPortCodes.append(origin)
        else:  # Region slug was given. Get the port codes for the region and descendants
            if not slug_exists(origin, connection):
                app.logger.error(f"Region {origin} does not exist.")
                return jsonify({"Error": f"Region {origin} does not exist."}), 400
            originPortCodes = get_port_codes(origin, connection)
        
        # For destination:
        if len(destination) <= 5 and destination.isupper():  # Port code was given
            if not port_code_exists(destination, connection):
                app.logger.error(f"Port {destination} does not exist.")
                return jsonify({"Error": f"Port {destination} does not exist."}), 400
            destinationPortCodes.append(destination)
        else:  # Region slug was given. Get the port codes for the region and descendants
            if not slug_exists(destination, connection):
                app.logger.error(f"Region {destination} does not exist.")
                return jsonify({"Error": f"Region {destination} does not exist."}), 400
            destinationPortCodes = get_port_codes(destination, connection)

        # Get price averages across all ports for each day in the range supplied
        with connection.cursor() as cursor:
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
    except psycopg2.Error as error:
        app.logger.error("Error fetching prices from the database: %s", error)
        return jsonify({'Error': 'Failed to fetch prices from the database. Please check your origin and destination.'}), 500
    finally:
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

# Checks if the port code exists in the ports table and returns true or false
def port_code_exists(port_code, connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS(SELECT 1 FROM ports WHERE code = %s);", (port_code,))
        exists = cursor.fetchone()[0]
        return exists

# Checks if the slug exists in the regions table and returns true or false
def slug_exists(slug, connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS(SELECT 1 FROM regions WHERE slug = %s);", (slug,))
        exists = cursor.fetchone()[0]
        return exists

# Retrieves the port codes for a given region slug and descendants.
# It uses a recursive query to traverse the region hierarchy.
# The function takes two parameters: the region slug and the database connection object.
# It returns a list of port codes associated with the given region.
def get_port_codes(region_slug, connection):
    port_codes = []
    with connection.cursor() as cursor:
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