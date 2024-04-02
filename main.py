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

class AnswerRequest(BaseModel):
    context: str = None
    question: str
    include_tables: list = None

@app.post("/answer/")
async def answer_question(request: AnswerRequest):
    """
    Get an answer to the provided question.
    Parameters:
    - request (AnswerRequest): The request body containing the question and optional context.
    Returns:
    - dict: A dictionary containing the answer.
    """
    db_engine = create_engine(odbc_str)
    
    if request.include_tables:
        include_tables = request.include_tables
    else:
        include_tables = ['Fact_Sales']  # Default tables
    
    db = SQLDatabase(db_engine, include_tables=include_tables)
    
    default_context_text =  """
                    You are a helpful AI assistant expert in identifying the relevant topic from user's question about Fact_Sales and then querying SQL Database to find answer.
                """
    llm = AzureChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL"),deployment_name=os.getenv("OPENAI_CHAT_MODEL"),temperature=0)
    sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_toolkit.get_tools()

    sqldb_agent = create_sql_agent(
        llm=llm,
        toolkit=sql_toolkit,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        agent_executor_kwargs={"return_intermediate_steps": True}
    )
    
    context_text = request.context if request.context else default_context_text
    context = ChatPromptTemplate.from_messages(
        [
            ("system",context_text),
            ("user", "{question}\n ai: "),
        ]
    )
    response = sqldb_agent.invoke(context.format(question=request.question))
    return {
        "answer": response["output"],
        "steps":response["intermediate_steps"]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
