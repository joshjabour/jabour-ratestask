from flask import Flask
import os
import psycopg2
app = Flask(__name__)

@app.route('/') 
def hello_geek():
    origin = "CNSGH"
    destination = "north_europe_main"
    originPortCodes = []
    try:
        connection = psycopg2.connect(
            host=os.environ['POSTGRES_DB_HOST'],
            database=os.environ['POSTGRES_DB_NAME'],
            user=os.environ['POSTGRES_USERNAME'],
            password=os.environ['POSTGRES_PASSWORD'])

        # Determine whether the a port code or a region slug was supplied for the origin and destination
        # ASSUMPTION: I've defined a port code as an upper-case string with 5 or fewer characters
        # If a port code was given, use only that port code. If it's a region slug, query the database
        # for all port codes in that region and its descendants
        if len(origin) <= 5 and origin.isupper():
            originPortCodes.append(origin) # Port code was given
        else:
            # Region slug was given. Query the database to return the port codes for region and descendants
            cursor = connection.cursor()
            cursor.execute("SELECT port_code FROM ports WHERE region_slug = %s", (origin,))
            originPortCodes = cursor.fetchall()
            cursor.close()
            

        if len(destination) <= 5 and destination.isupper():
            destinationPortCodes.append(destination)

    except psycopg2.Error as error:
        print("Error fetching data from the database:", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

    # Query the database to return the average prices for the given origin and destination
    cursor = connection.cursor()
    
    cursor.execute("SELECT port_code FROM ports")
    destinationPortCodes = cursor.fetchall()
    cursor.close()
    connection.close()
    return '<h1>Hello from Flask & Docker' + os.environ['POSTGRES_USERNAME'] + '</h2>'


if __name__ == "__main__":
    app.run(debug=True)