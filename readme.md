To run this,

1. Start the docker engine
2. Go to the folder where the compose.yaml is
3. Open a terminal in that file path.
4. Run the command "docker compose build"
5. Run the command "docker compose up"
6. After containers are ready run the command below:
docker exec -it aidata_engineer_task-airflow-1 airflow users create --username mert --password mert --firstname mert --lastname mert --role Admin --email email
7. Go to http://localhost:8080/ for Apache Airflow, the username and the password are both mert.
8. Go to http://localhost:3000/ for Grafana, the username and the password are both admin
9. To add our data source in Grafana, click Data sources on the left
10. Add new data source
11. Choose PostgreSQL from the list
12. Here are the credentials for our database:
	Host URL = postgres:5432
	Database Name = incidence_database
	Username = postgres
	Password = mert
13. Choose TLS/SSL Mode as disable.
14. Save & test