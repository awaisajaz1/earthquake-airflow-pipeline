from airflow.sdk import dag, task
from airflow.operator.bash import BashOperator
from airflow.operator.python import PythonOperator


@dag(dag_id="xcom_dag_automation", schedule_interval="@daily", start_date=datetime(2023, 1, 1), catchup=False)
def modern_dag_automation():

    @task.python
    def first_task():
        print("Hello World!")
        return {"data": [1,2,3]}


    @task.python
    def second_task(dictionary: dict):
        print(dictionary.get("data"))

        transformed_data = dictionary.get("data")
        return transformed_data * 2
    
    @task.python
    def third_task(transformed_data: list):
        print(transformed_data)


    # define tasks dependencies
    first_task = first_task()
    second_task = second_task(first_task)
    third_task = third_task(second_task)

modern_dag_automation()



    


           