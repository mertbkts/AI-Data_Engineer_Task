from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
import re
import json
import psycopg2
import logging


def count_incidence(website, tag, class_=None, keywords=None):
    response = requests.get(website[1])
    soup = BeautifulSoup(response.content, "html.parser")

    # Compiling regex patterns for each keyword
    keyword_patterns = {
        keyword: re.compile(r"\b{}\b".format(keyword)) for keyword in keywords
    }

    if class_:
        headlines = soup.find_all(tag, class_=class_)
    else:
        headlines = soup.find_all(tag)

    results = []

    for keyword, pattern in keyword_patterns.items():
        count = 0
        for headline in headlines:
            if pattern.search(headline.get_text()):
                count += 1
                # print(headline.get_text())
        results.append(
            {
                "term": keyword,
                "incidence": count,
                "site": website[0],
                "timestamp": datetime.now().isoformat(),
            }
        )
    return results


def run_crawler():

    logging.info("This is an informational message")
    
    keywords=["election", "war", "economy"]
    websites={"ft": "https://www.ft.com/", "tg": "https://www.theguardian.com/europe"}
    combined_results = []

    for website in websites.items():
        if website[0] == "ft":
            results = count_incidence(website, "div", "headline", keywords=keywords)
        else:
            results = count_incidence(
                website, ["h1", "h2", "h3", "h4", "h5", "h6"], keywords=keywords
            )

        combined_results.extend(results)

    with open("/opt/airflow/dags/combined_results.json", "w") as outfile:
        json.dump(combined_results, outfile, indent=4)



def insert_data_to_table():
    connection = psycopg2.connect(
        dbname="incidence_database",
        user="postgres",
        password="mert",
        host="postgres",
    )
    
    cur = connection.cursor()

    # # Uncomment to drop the existing table
    # cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'incidence_table')")
    # table_exists = cur.fetchone()[0]
    # if table_exists:
    #     cur.execute("DROP TABLE incidence_table")
    #     print("Successfully deleted table 'incidence_table'")
    # else:
    #     print("Table 'incidence_table' does not exist")

    cur.execute("SELECT 1 FROM pg_database WHERE datname='incidence_database'")
    database_exists = cur.fetchone()

    if not database_exists:
        cur.execute("CREATE DATABASE incidence_database")
        print("Successfully created database 'incidence_database'")

    
    cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'incidence_table')")
    table_exists = cur.fetchone()[0]

    if not table_exists:
        cur.execute("""
            CREATE TABLE incidence_table (
                id SERIAL PRIMARY KEY,
                term VARCHAR(20),
                incidence INTEGER,
                site VARCHAR(10),
                timestamp TIMESTAMP
            )
        """)
        print("Successfully created table 'incidence_table'")

    with open("/opt/airflow/dags/combined_results.json", "r") as file:
        structured_data = json.load(file)

    for item in structured_data:
        #timestamp = datetime.strptime(item["timestamp"], "%Y-%m-%d").replace(hour=0, minute=0, second=0)
        cur.execute(
            """
            INSERT INTO incidence_table (term, incidence, site, timestamp)
            VALUES (%s, %s, %s, %s)
            """,
            (item["term"], item["incidence"], item["site"], item["timestamp"]),
        )

    connection.commit()

    cur.close()
    connection.close()


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 9),
}

days_except_friday_dag = DAG(
    'days_except_friday_dag',
    default_args=default_args,
    description='A DAG to crawl websites, count keyword incidences and insert them into a database',
    schedule_interval='0 */2 * * 0-4,6', # Run every 2 hours for days of the week
)

except_friday_crawler_task = PythonOperator(
    task_id='except_friday_crawler_task',
    python_callable=run_crawler,
    dag=days_except_friday_dag,
)

except_friday_run_database_task = PythonOperator(
    task_id='except_friday_run_database_task',
    python_callable=insert_data_to_table,
    dag=days_except_friday_dag,
)

except_friday_crawler_task >> except_friday_run_database_task

friday_dag = DAG(
    'friday_dag',
    default_args=default_args,
    description='A DAG to crawl websites, count keyword incidences and insert them into a database',
    schedule_interval='0 */1 * * 5', # Run every hour on Fridays
)

friday_crawler_task = PythonOperator(
    task_id='friday_crawler_task',
    python_callable=run_crawler,
    dag=friday_dag,
)

friday_run_database_task = PythonOperator(
    task_id='friday_run_database_task',
    python_callable=insert_data_to_table,
    dag=friday_dag,
)

friday_crawler_task >> friday_run_database_task
