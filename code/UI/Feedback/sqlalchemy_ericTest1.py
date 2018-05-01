#!/usr/bin/python3
# Trivial sample program fiddling with SQLAlchemy

import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
 
class Person(Base):
    __tablename__ = 'person'
    # Here we define columns for the table person
    # Notice that each column is also a normal Python instance attribute.
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
 
class Address(Base):
    __tablename__ = 'address'
    # Here we define columns for the table address.
    # Notice that each column is also a normal Python instance attribute.
    id = Column(Integer, primary_key=True)
    street_name = Column(String(250))
    street_number = Column(String(250))
    post_code = Column(String(250), nullable=False)
    person_id = Column(Integer, ForeignKey('person.id'))
    person = relationship(Person)


def main():
  print("Creating database")
  engine = create_engine('sqlite:///sqlalchemy_example.db')
  Base.metadata.create_all(engine)

  print("Writing to database")
  DBSession = sessionmaker(bind=engine)
  session = DBSession()
  new_person = Person(name='Eric')
  session.add(new_person)
  session.commit()
  new_address = Address(post_code='98008', person=new_person)
  session.add(new_address)
  session.commit()

  print("Querying database")
  for person in session.query(Person).all():
    print(person)
    print("id="+str(person.id)+"  name="+person.name+"\n")
    

if __name__ == "__main__": main()
