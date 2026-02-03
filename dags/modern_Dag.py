from airflow.sdk import dag, task
from datetime import datetime

@dag(dag_id="xcom_dag_automation")
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
    def third_task(transformed_data: list, **kwargs):
        print(transformed_data)
        ti = kwargs.get("ti")
        # Manual XCOM push
        ti.xcom_push(key = "transformed_data", value = transformed_data)
        # Don't return anything (or return None) to break automatic XCom chain
    
    @task.python
    def fourth_task(**kwargs):
        ti = kwargs.get("ti")
        transformed_data = ti.xcom_pull(key = "transformed_data")
        print(transformed_data, "Owais this is manual xcom")
        return transformed_data




    # define tasks dependencies
    first_task = first_task()
    second_task = second_task(first_task)
    third_task = third_task(second_task)
    fourth_task = fourth_task()

    third_task >> fourth_task
modern_dag_automation()



    


           