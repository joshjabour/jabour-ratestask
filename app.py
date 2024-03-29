from flask import Flask
import logging
import os
import psycopg2
app = Flask(__name__)

@app.route('/') 
def hello_geek():
    date_from = "2016-01-01"
    date_to = "2016-01-05"
    origin = "CNSGH"
    destination = "north_europe_main"
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

        # Format the port codes for use in the SQL query
        originPortCodes = ','.join([f"{code}" for code in originPortCodes])
        destinationPortCodes = ','.join([f"{code}" for code in destinationPortCodes])

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
                    orig_code IN(%s) AND
                    dest_code IN(%s)
            GROUP BY days.day;
            ''', (date_from, date_to, originPortCodes, destinationPortCodes))
        prices = cursor.fetchall()
        cursor.close()

    except psycopg2.Error as error:
        app.logger.error("Error fetching prices from the database: %s", error)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
    return '<h1>Hello from Flask & Docker</h2><p>' + str(prices) + '</p>'

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