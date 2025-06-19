from sqlalchemy import Column, String, create_engine 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
Base=declarative_base()

class uploaded_judgements(Base):
    __tablename__ = 'uploaded_judgements'
    id=Column(String, primary_key=True)
    matter_no=Column(String)
    order_date=Column(String)
    drive_file_id=Column(String)

engine=create_engine('sqlite:///judgements.db')
Base.metadata.create_all(engine)
SessionLocal=sessionmaker(bind=engine)
