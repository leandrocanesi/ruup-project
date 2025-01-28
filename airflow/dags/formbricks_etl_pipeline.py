from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Configurações gerais do DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'formbricks_etl_pipeline',
    default_args=default_args,
    description='Pipeline ETL para dados do Formbricks',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
)

# Função para coletar dados da pesquisa "Pesquisa de Satisfação RUUP"
def collect_data_from_api(**kwargs):
    api_key = 'bbe1c3d86344bbc31d818818aca463b8'
    survey_id = 'xzl6wgn7i694oambym57kn8r'  # ID da pesquisa desejada
    url = f'http://formbricks:3000/api/v1/management/responses?surveyId={survey_id}'
    headers = {'x-api-key': api_key}

    # Fazendo a requisição para obter as respostas
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        responses = data.get('data', [])
        if responses:
            df = pd.DataFrame(responses)
            df.to_csv('/opt/airflow/dags/bronze_data.csv', index=False)  # Camada Bronze
            print("Dados salvos na camada Bronze.")
        else:
            raise ValueError("Nenhuma resposta encontrada para a pesquisa.")
    else:
        raise RuntimeError(f"Erro ao coletar dados: {response.status_code}, {response.text}")

# Função para transformação inicial dos dados (Camada Prata)
def transform_data(**kwargs):
    df = pd.read_csv('/opt/airflow/dags/bronze_data.csv')
    df.dropna(inplace=True)  # Remover valores nulos
    df.drop_duplicates(inplace=True)  # Remover duplicados
    df.to_csv('/opt/airflow/dags/silver_data.csv', index=False)  # Camada Prata

    # Visualização da Camada Prata
    print("Transformação para Camada Prata completa:")
    print(df.head())

# Função para processamento avançado e visualização (Camada Ouro)
def process_and_visualize_data(**kwargs):
    df = pd.read_csv('/opt/airflow/dags/silver_data.csv')
    # Exemplo de análise: contagem de respostas por pergunta
    if 'question_id' in df.columns:
        analysis = df['question_id'].value_counts()
        plt.figure(figsize=(10, 6))
        analysis.plot(kind='bar')
        plt.title('Contagem de Respostas por Pergunta')
        plt.xlabel('ID da Pergunta')
        plt.ylabel('Número de Respostas')
        plt.savefig('/opt/airflow/dags/analysis_plot.png')  # Salvar gráfico
        print("Gráfico gerado: /opt/airflow/dags/analysis_plot.png")
    else:
        print("A coluna 'question_id' não foi encontrada no conjunto de dados.")
    # Salvar dados processados
    df.to_csv('/opt/airflow/dags/gold_data.csv', index=False)

# Função para exportar dados para Excel
def export_to_excel(**kwargs):
    df = pd.read_csv('/opt/airflow/dags/gold_data.csv')
    df.to_excel('/opt/airflow/dags/final_data.xlsx', index=False)
    print("Dados exportados para Excel: /opt/airflow/dags/final_data.xlsx")

# Dummy Operator para iniciar o pipeline
start = DummyOperator(
    task_id='start',
    dag=dag,
)

# Definição das tarefas no Airflow
t1 = PythonOperator(
    task_id='collect_data_from_api',
    python_callable=collect_data_from_api,
    dag=dag,
)

t2 = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag,
)

t3 = PythonOperator(
    task_id='process_and_visualize_data',
    python_callable=process_and_visualize_data,
    dag=dag,
)

t4 = PythonOperator(
    task_id='export_to_excel',
    python_callable=export_to_excel,
    dag=dag,
)

# Dummy Operator para finalizar o pipeline
end = DummyOperator(
    task_id='end',
    dag=dag,
)

# Definindo a sequência das tarefas
start >> t1 >> t2 >> t3 >> t4 >> end
