from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from sqlalchemy import create_engine
from fastapi import FastAPI, Query
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate

load_dotenv()

app = FastAPI()

driver = '{ODBC Driver 18 for SQL Server}'
odbc_str = 'mssql+pyodbc:///?odbc_connect=' \
                'Driver='+driver+ \
                ';Server=tcp:' + os.getenv("SQL_SERVER")+'.database.windows.net;PORT=1433' + \
                ';DATABASE=' + os.getenv("SQL_DB") + \
                ';Uid=' + os.getenv("SQL_USERNAME")+ \
                ';Pwd=' + os.getenv("SQL_PWD") + \
                ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

db_engine = create_engine(odbc_str)

# include_tables=['Fact_SalesOrderItem','Dim_Product']
include_tables=['Dim_Currency']

db = SQLDatabase(db_engine, include_tables=include_tables)

llm = AzureChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL"),deployment_name=os.getenv("OPENAI_CHAT_MODEL"),temperature=0)
default_context = ChatPromptTemplate.from_messages(
    [
        ("system",
            """
            You are a helpful AI assistant expert in identifying the relevant topic from user's question about Dim_Currency and then querying SQL Database to find answer.
            """
        ),
        ("user", "{question}\n ai: "),
    ]
)
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
sql_toolkit.get_tools()

sqldb_agent = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

class AnswerRequest(BaseModel):
    question: str
    context: str = None

@app.post("/answer/")
async def answer_question(request: AnswerRequest):
    """
    Get an answer to the provided question.

    Parameters:
    - request (AnswerRequest): The request body containing the question and optional context.

    Returns:
    - dict: A dictionary containing the answer.
    """
    context = request.context if request.context else default_context
    response = sqldb_agent.run(context.format(question=request.question))
    return {"answer": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
