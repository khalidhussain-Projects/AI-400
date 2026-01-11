import os

from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Field, create_engine, Session, select
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# DB Configuration with create_engine
DB_URL = os.getenv("DB_URL")

engine = create_engine(DB_URL, echo=True)

#how to create tables and DB structure
#def create_db_and_tables():
#   SQLModel.metadata.create_all(engine)    

# DB STRUCTURE/TABLES and same will be used at API ENDPOINTS.

class Task(SQLModel, table=True):
    id: int |None = Field(default=None, primary_key=True)
    title: str
    description: str |None = Field(default=None)

# Initialize the database and migrate tables
#create_db_and_tables()

#how to interact with DB using Session
def get_session():  
        with Session(engine) as session:
            yield session

# app is the instace of FastAPI
app = FastAPI()



@app.post("/tasks")
def create_Task(task: Task, session: Session = Depends(get_session)):
       session.add(task)
       session.commit()
       session.refresh(task)
       return task


@app.get("/tasks")
def get_Tasks(session: Session = Depends(get_session)):
        tasks = session.exec(select(Task)).all()
        return tasks

@app.get("/tasks/{task_id}")
def get_Task(task_id: int, session: Session = Depends(get_session)):
        task = session.get(Task, task_id)
        return task

# patch a task by id
@app.patch("/tasks/{task_id}")
def patch_Task(task_id: int, updated_task: Task, session: Session = Depends(get_session)):
        task = session.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        if updated_task.title is not None:
            task.title = updated_task.title
        if updated_task.description is not None:
            task.description = updated_task.description
        session.add(task)
        session.commit()
        session.refresh(task)
        return task     


#update a task by id
@app.put("/tasks/{task_id}")
def update_Task(task_id: int, updated_task: Task, session: Session = Depends(get_session)):
        task = session.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        task.title = updated_task.title
        task.description = updated_task.description
        session.add(task)
        session.commit()
        session.refresh(task)
        return task

#delete a task by id
@app.delete("/tasks/{task_id}")
def delete_Task(task_id: int, session: Session = Depends(get_session)):
        task = session.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}
        session.delete(task)
        session.commit()
        return {"message": "Task deleted successfully"}
