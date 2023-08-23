import urllib3
import pandas as pd
import json
import boto3
import os
import os
import psycopg2

s3 = boto3.client("s3")
# Load environment variables from the .env file

def lambda_handler(event, context):
    # TODO implement

    http = urllib3.PoolManager()

    url = os.environ["URL"]
    
    
    headers = {
    'X-RapidAPI-Key': os.environ['RapidAPIKey'],
    'X-RapidAPI-Host': os.environ["RapidAPIHost"]
    }

    # GET DATA
    response = http.request("GET", url, headers=headers)
    
    data = response.data.decode("utf-8")
    
    data_dict = json.loads(data)
    
    
    # Save raw data to bucket
    s3.put_object(Body=response.data, Bucket='apprentice-ml-muskan-learning-dev',Key='raw_nba_data/raw_nba.json')
    
    json_data = data_dict["data"]

    df = pd.json_normalize(json_data)
    
    df['full_name'] = df['first_name'] + ' ' + df['last_name']

    # Drop the original first_name and last_name columns
    df.drop(['first_name', 'last_name'], axis=1, inplace=True)
    
    # Calculate the median of the 'weight_pounds' column
    weight_median = df['weight_pounds'].median()
    
    # Fill missing values with the median
    df['weight_pounds'].fillna(weight_median, inplace=True)
    
    # Calculate the medians of the 'height_feet' and 'height_inches' columns
    height_feet_median = df['height_feet'].median()
    height_inches_median = df['height_inches'].median()
    
    # Fill missing values in 'height_feet' and 'height_inches' columns with their respective medians
    df['height_feet'].fillna(height_feet_median, inplace=True)
    df['height_inches'].fillna(height_inches_median, inplace=True)
    
    df.rename(columns={
        'team.id': 'team_id',
        'team.abbreviation': 'team_abbreviation',
        'team.city': 'team_city',
        'team.conference': 'team_conference',
        'team.division': 'team_division',
        'team.full_name': 'team_full_name',
        'team.name': 'team_name'
    }, inplace=True)
    
    # RDS
    # Connection Code
    try:
        conn = psycopg2.connect(
            host = os.environ['HOST_NAME'],
            database = os.environ['DB_NAME'],
            user = os.environ['DB_USER'],
            password = os.environ['PASSWORD']
        )
        print("Connected to postgres")
    except Exception as e:
        print(e)
    
    cursor = conn.cursor()
    
    table_name = os.environ["TABLE_NAME"]
    
    # Create table
    
    cursor.execute("""
    Create table etl_muskan_nba_table(
    id SERIAL PRIMARY KEY,
    height_feet INT,
    height_inches INT,
    position VARCHAR(255),
    weight_pounds INT,
    team_id INT,
    team_abbreviation VARCHAR(255),
    team_city VARCHAR(255),
    team_conference VARCHAR(255),
    team_division VARCHAR(255),
    team_full_name VARCHAR(255),
    team_name VARCHAR(255),
    full_name VARCHAR(255)
    )
    """)
    
    conn.commit()
    
    data_to_insert = [tuple(row) for row in df.values]

    
    insert_query = f"""
    INSERT INTO {table_name}
    (id, height_feet, height_inches, position, weight_pounds, team_id, team_abbreviation, team_city, team_conference, team_division, team_full_name, team_name, full_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # Insert data using the cursor
    cursor.executemany(insert_query, data_to_insert)

    # Commit the transaction
    conn.commit()
    
    cleaned_json = df.to_json(orient='records')
    s3.put_object(Body=cleaned_json, Bucket='apprentice-ml-muskan-cleaned-learning-dev',Key='cleaned_data/cleaned_data.json')
