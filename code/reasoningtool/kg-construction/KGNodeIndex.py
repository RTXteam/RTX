#!/usr/bin/python3
#
# Class to build and query an index of nodes in the KG
#
import os
import sys
import re
import timeit

from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

#### Define the database tables as classes
class KGNode(Base):
  __tablename__ = 'kgnode'
  kgnode_id = Column(Integer, primary_key=True)
  curie = Column(String(255), nullable=False, index=True)
  name = Column(String(255), nullable=False, index=True)
  type = Column(String(255), nullable=False)

#### Main class
class KGNodeIndex:

  #### Constructor
  def __init__(self):
    filepath = os.path.dirname(os.path.abspath(__file__))
    is_rtx_production = False
    if re.match("/mnt/data/orangeboard",filepath):
      is_rtx_production = True
    #print("is_rtx_production="+str(is_rtx_production))

    if is_rtx_production:
      self.databaseName = "RTXFeedback"
    else:
      self.databaseName = "KGNodeIndex.sqlite"
    self.engine = None
    self.session = None

  #### Destructor
  def __del__(self):
    self.disconnect()
    pass

  #### Define attribute session
  @property
  def session(self) -> str:
    return self._session

  @session.setter
  def session(self, session: str):
    self._session = session


  #### Define attribute engine
  @property
  def engine(self) -> str:
    return self._engine

  @engine.setter
  def engine(self, engine: str):
    self._engine = engine


  #### Define attribute databaseName
  @property
  def databaseName(self) -> str:
    return self._databaseName

  @databaseName.setter
  def databaseName(self, databaseName: str):
    self._databaseName = databaseName


  #### Delete and create the SQLite database. Careful!
  def createDatabase(self):
    if re.search("sqlite",self.databaseName):
      if os.path.exists(self.databaseName):
        print("INFO: Removing previous database "+self.databaseName)
        os.remove(self.databaseName)

    print("INFO: Creating database "+self.databaseName)
    if re.search("sqlite",self.databaseName):
      engine = create_engine("sqlite:///"+self.databaseName)
    else:
      engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)
    Base.metadata.create_all(engine)


  #### Create and store a database connection
  def connect(self):
    if self.session is not None:
      return
    if re.search("sqlite",self.databaseName):
      if not os.path.isfile(self.databaseName):
        self.createDatabase()

    print("INFO: Connecting to database")
    if re.search("sqlite",self.databaseName):
      engine = create_engine("sqlite:///"+self.databaseName)
    else:
      engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    self.session = session
    self.engine = engine


  #### Create and store a database connection
  def disconnect(self):
    session = self.session
    engine = self.engine
    if self.session is None or self.engine is None:
      print("INFO: Skip disconnecting from database")
      return
    print("INFO: Disconnecting from database")
    session.close()
    print(engine)
    engine.dispose()
    self.session = None
    self.engine = None

  #### Create the KG node table
  def createNodeTable(self):

    self.connect()
    session = self.session
    engine = self.engine
    if re.search("sqlite",self.databaseName):
      pass
    else:
      engine.execute("TRUNCATE TABLE kgnode")

    lineCounter = 0
    try:
      fh = open("../../../data/KGmetadata/NodeNamesDescriptions.tsv", 'r', encoding="latin-1", errors="replace")
    except FileNotFoundError:
      fh = open("../../data/KGmetadata/NodeNamesDescriptions.tsv", 'r', encoding="latin-1", errors="replace")
    for line in fh.readlines():
      columns = line.strip("\n").split("\t")
      curie = columns[0] # TODO: note that this is not actually the curie, but the rtx_name. Should change KG meta dump to use curie instead, and sed replace rtx_name with id
      name = columns[1]
      type = "?"

      names = [ name ]

      if re.match("OMIM:",curie):
        type = "disease"
        multipleNames = name.split("; ")
        if len(multipleNames) > 1:
          for possibleName in multipleNames:
            if possibleName == multipleNames[0]:
              next
            names.append(possibleName)

      elif re.match("DOID",curie):
        type = "disease"

      elif re.match("R-HSA-",curie):
        type = "pathway"
        if re.search(r' \([A-Z0-9]{1,8}\)',name):
          newName = re.sub(r' \([A-Z0-9]{1,8}\)',"",name,flags=re.IGNORECASE)
          names.append(newName)
          #print("  duplicated _"+name+"_ to _"+newName+"_")

      elif re.match("NCBIGene:",curie):
        type = "microRNA"

      elif re.match("UBERON:",curie):
        type = "anatomical_part"

      elif re.match("CL:",curie):
        type = "cell_type"

      elif re.match("AQTLTrait:",curie):
        type = "phenotype"

      elif re.match("HP:",curie):
        type = "phenotype"

      elif re.match("GO:",curie):
        type = "process"

      elif re.match("[A-Z][A-Z0-9]{5}",curie) or re.match("A[A-Z0-9]{9}",curie):
        type = "protein"
        names.append(curie)

      elif re.match("[A-Z0-9]+\_HUMAN",curie):
        type = "protein"

      else:
        print("No match for: "+curie)
        break

      #### Create duplicates for various DoctorName's diseases
      for name in names:
        if re.search("'s ",name):
          newName = re.sub("'s ","s ",name)
          names.append(newName)
          #print("  duplicated _"+name+"_ to _"+newName+"_")
          newName = re.sub("'s "," ",name)
          names.append(newName)
          #print("  duplicated _"+name+"_ to _"+newName+"_")

      #### A few special cases
      if re.search("alzheimer ",name,flags=re.IGNORECASE):
        newName = re.sub("alzheimer ","alzheimers ",name,flags=re.IGNORECASE)
        names.append(newName)
        #print("  duplicated _"+name+"_ to _"+newName+"_")

        newName = re.sub("alzheimer ","alzheimer's ",name,flags=re.IGNORECASE)
        names.append(newName)
        #print("  duplicated _"+name+"_ to _"+newName+"_")

      #### Add all the possible names to the database
      namesDict = {}
      for name in names:
        name = name.upper()
        if name in namesDict:
          continue
        #print(type+" "+curie+"="+name)
        kgnode = KGNode(curie=curie,name=name,type=type)
        session.add(kgnode)
        namesDict[name] = 1

      #### Commit every now and then
      if int(lineCounter/1000) == lineCounter/1000:
        session.commit()
        print(str(lineCounter)+"..",end='',flush=True)

      #### Throttle the system for testing
      lineCounter += 1
      #if lineCounter > 100:
      #  break

    fh.close()
    session.flush()
    print("")


  def createIndex(self):
    self.connect()
    engine = self.engine
    #engine.execute("DROP INDEX idx_name ON kgnode")
    #engine.execute("CREATE INDEX idx_name ON kgnode(name)")


  def get_curies(self,name):
    self.connect()
    session = self.session
    matches = session.query(KGNode).filter(KGNode.name==name.upper()).all()
    if matches is None:
      return None
    curies = []
    for match in matches:
      curies.append(match.curie)
    return(curies)


  def is_curie_present(self,curie):
    self.connect()
    session = self.session
    match = session.query(KGNode).filter(KGNode.curie==curie).first()
    if match is None:
      return(False)
    return(True)


def main():
  kgNodeIndex = KGNodeIndex()

  #### To rebuild
  if re.search("sqlite",kgNodeIndex.databaseName):
    if not os.path.exists(kgNodeIndex.databaseName):
      kgNodeIndex.createDatabase()
      kgNodeIndex.createNodeTable()
      #kgNodeIndex.createIndex()

  print("==== Testing for finding curies by name ====")
  tests = [ "APS2", "phenylketonuria","Gaucher's disease","Gauchers disease","Gaucher disease",
    "Alzheimer Disease","Alzheimers disease","Alzheimer's Disease","kidney","Kidney","P06865","HEXA",
    "rickets","fanconi anemia","retina" ]

  t0 = timeit.default_timer()
  for test in tests:
    curies = kgNodeIndex.get_curies(test)
    print(test+" = "+str(curies))
  t1 = timeit.default_timer()
  print("Elapsed time: "+str(t1-t0))


  print("==== Testing presence of CURIEs ============================")
  tests = [ "R-HSA-2160456", "DOID:9281", "OMIM:261600", "DOID:1926xx", "HP:0002511", "UBERON:0002113", "P06865", "DOID:13636", "OMIM:104300", "DOID:10652xx" ]

  t0 = timeit.default_timer()
  for test in tests:
    is_present = kgNodeIndex.is_curie_present(test)
    print(test+" = "+str(is_present))
  t1 = timeit.default_timer()
  print("Elapsed time: "+str(t1-t0))


if __name__ == "__main__":
  main()

