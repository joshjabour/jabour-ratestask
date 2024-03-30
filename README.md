# Introduction
This is a code submission by Josh Jabour for the rates task provided by Xeneta.

# Initial Setup with Docker

You must have the ability to run docker containers to test this application.

Start by cloning the repository.

Next, create a network so the db container and the app container can talk to each other:

```bash
docker network create ratestasknetwork
```

Execute the provided Dockerfiles by running:

```bash
docker build -t ratesdb . --target db
docker build -t ratesapp . --target app
```

This will create containers with the names *ratesdb* and *ratesapp*, which you can start in the following way:

```bash
docker run -d --network=ratestasknetwork -p 0.0.0.0:5432:5432 --name ratesdb ratesdb
docker run -d --network=ratestasknetwork -p 0.0.0.0:80:5000 --name ratesapp ratesapp
```

Once the containers have started you can access the API by running a curl command as follows:

```bash
curl "http://127.0.0.1/rates?date_from=2016-01-01&date_to=2016-01-10&origin=CNSGH&destination=north_europe_main"
```

For some lite automated testing you can run this:
```bash
docker run --rm ratesapp pytest
```

When you’re finished you can use the following command to shut down the containers and remove them:

```bash
docker stop ratesdb
docker stop ratesapp
docker rm ratesdb
docker rm ratesapp
```

# API Spec

Every API endpoint must have documentation. As such, I have included an API specification with the filename api_spec.yaml.

# Test Cases and Results

I wouldn't normally include test cases in a readme file, but in the effort to make this work submission complete I am sharing documentation of the tests I've performed and their results.

| Test Case | date_from  | date_to    | origin           | destination       | Results                                                                                   | Pass/Fail |
|-----------|------------|------------|------------------|-------------------|--------------------------------------------------------------------------------------------|-----------|
| 1         | 2016-01-01 | 2016-01-10 | north_europe_main| CNSGH             | Matches results provided in readme. For average_price, 3+ rates gives the rounded average, 1-2 rates gives null, and 0 rates gives null. | PASS      |
| 2         | 2016-01-01 | 2016-01-10 | CNSGH            | north_europe_main | Includes dates, but average_price are all nulls because no records exist for this route   | PASS      |
| 3         | 2016-01-01 | 2016-01-10 | china_main       | NLRTM             | PASS (checked results using manual queries)                                               | PASS      |
| 4         | 2016-01-01 | 2016-01-10 | china_main       | northern_europe   | PASS (checked results using manual queries)                                               | PASS      |
| 5         | 2016-01-01 | 2016-01-10 | CNGGZ            | EETLL             | PASS (checked results using manual queries)                                               | PASS      |
| 6         | **2016-01-10** | **2016-01-01** | CNGGZ            | EETLL             | "Error": "Invalid date range. The date_from must be earlier than the date_to"             | PASS      |
| 7         | **2016-13-01** | **2016-13-10** | CNGGZ            | EETLL             | "Error": "Invalid date format"                                                            | PASS      |
| 8         | 2016-01-01 | 2016-01-10 | CNGGZ            | **Null**              | "Error": "Missing query parameters"                                                       | PASS      |
| 9         | 2016-01-01 | 2016-01-10 | CNGGZ            | **XXXXX**             | "Error": "Port code XXXXX does not exist."                                                | PASS      |
| 10        | 2016-01-01 | 2016-01-10 | CNGGZ            | **northern_europ**    | "Error": "Region northern_europ does not exist."                                          | PASS      |

# Time Spent

I spent 6 hours writing the code for this application. After that, I performed some testing and finalized the documentation.

# Difficulties

1. Initially, I tried to use only SQL to determine whether the origin and destination inputs were a port codes or slugs, and that resulted in some lost time. I found a way to make it work, but the code was too complex. To resolve this, I removed the SQL and wrote python code for the task. The python code is much cleaner.
1. I had a challenge setting up my docker containers because I tried to set environment variables at the top of the dockerfile. This caused the build to fail, and that error took me a few minutes to resolve.

# Opportunities for Improving this Application

The application I am submitting is a fully-functional application that performs as required. However, given more time there are additional steps that I would take to improve the application:
1. Instead of having to set up a network and running two docker containers separately, they should be combined and run using one docker-compose command.
1. I've included some basic pytest automated tests to check for input errors. However, these tests do not fully test the application. Additional tests that mock the database are needed to provide complete coverage.
1. One potential improvement for the API response is during the case that the origin and destination are valid but have no price data for the given period. Given that scenario, my application currently returns a null average_price for each date. But it might be more user-friendly to provide a succinct message stating that there are no prices matching the given parameters.

# Feedback on ratestask Repository Setup

I noticed when reviewing the ratestest repository that I can see 14 forked repositories, and I assume they contain solutions. I did not view the code in any of them, but I want to flag this as a vulnerability with the task because someone might be plagiarising without your knowledge (unless you are carefully checking against all forks of the repository). My recommendation is to make the ratestask repository private, disallow forking, and add candidates as contributors when they are to perform the task.

# Thank You!

Thank you for viewing this submission! I thoroughly enjoyed completing this task, and I appreciate your time for reviewing it.