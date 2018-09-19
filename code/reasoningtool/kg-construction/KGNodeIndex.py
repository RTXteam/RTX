#!/usr/bin/python3
#
# Class to build and query an index of nodes in the KG
#
import os
import sys
import re
import timeit
import argparse

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

#### Testing and debugging flags
DEBUG = False
TESTSUFFIX = ""
#TESTSUFFIX = "_test2"


#### Define the database tables as classes
class KGNode(Base):
  __tablename__ = "kgnode" + TESTSUFFIX
  kgnode_id = Column(Integer, primary_key=True)
  curie = Column(String(255), nullable=False, index=True)
  name = Column(String(255), nullable=False, index=True)
  type = Column(String(255), nullable=False)

class KGNodeSource(Base):
  __tablename__ = "kgnode_source" + TESTSUFFIX
  kgnode_source_id = Column(Integer, primary_key=True)
  mtime = Column(DateTime, nullable=False)


#### Main class
class KGNodeIndex:

  #### Constructor
  def __init__(self):
    filepath = os.path.dirname(os.path.abspath(__file__))
    is_rtx_production = False
    if re.match("/mnt/data/orangeboard",filepath):
      is_rtx_production = True
    if DEBUG: print("is_rtx_production="+str(is_rtx_production))

    if is_rtx_production:
      self.databaseName = "RTXFeedback"
      self.engine_type = "mysql"
    else:
      self.databaseName = "KGNodeIndex.sqlite"
      self.engine_type = "sqlite"
    self.engine = None
    self.session = None


  #### Destructor
  def __del__(self):
    if self.engine_type == "mysql":
      self.disconnect()
    else:
      pass


  #### session
  @property
  def session(self) -> str:
    return self._session
  @session.setter
  def session(self, session: str):
    self._session = session


  #### engine
  @property
  def engine(self) -> str:
    return self._engine
  @engine.setter
  def engine(self, engine: str):
    self._engine = engine


  #### engine_type
  @property
  def engine_type(self) -> str:
    return self._engine_type
  @engine_type.setter
  def engine_type(self, engine_type: str):
    self._engine_type = engine_type


  #### databaseName
  @property
  def databaseName(self) -> str:
    return self._databaseName
  @databaseName.setter
  def databaseName(self, databaseName: str):
    self._databaseName = databaseName


  #### Delete and create the SQLite database. Careful!
  def createDatabase(self):
    if self.engine_type == "sqlite":
      if os.path.exists(self.databaseName):
        if DEBUG is True: print("INFO: Removing previous database "+self.databaseName)
        os.remove(self.databaseName)

    if DEBUG is True: print("INFO: Creating database "+self.databaseName)
    if self.engine_type == "sqlite":
      engine = create_engine("sqlite:///"+self.databaseName)
    else:
      engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)

    Base.metadata.create_all(engine)


  #### Create and store a database connection
  def connect(self):
    if self.session is not None: return
    if self.engine_type == "sqlite":
      if not os.path.isfile(self.databaseName):
        self.createDatabase()

    #### Create an engine object
    if DEBUG is True: print("INFO: Connecting to database")
    if self.engine_type == "sqlite":
      engine = create_engine("sqlite:///"+self.databaseName)
    else:
      engine = create_engine("mysql+pymysql://rt:Steve1000Ramsey@localhost/"+self.databaseName)

    #### Create the session. This is weird syntax
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    #### Save these for later retrieval
    self.session = session
    self.engine = engine


  #### Destroy the database connection
  def disconnect(self):
    session = self.session
    engine = self.engine

    if self.session is None or self.engine is None:
      if DEBUG is True: print("INFO: Skip disconnecting from database")
      return

    if DEBUG is True: print("INFO: Disconnecting from database")
    session.close()
    engine.dispose()
    self.session = None
    self.engine = None


  #### Create the KG node table
  def createNodeTable(self):

    self.connect()
    session = self.session
    engine = self.engine
    if self.engine_type == "sqlite":
      pass
    else:
      engine.execute( "TRUNCATE TABLE kgnode" + TESTSUFFIX )

    lineCounter = 0
    fh = open( os.path.dirname(os.path.abspath(__file__)) + "/../../../data/KGmetadata/NodeNamesDescriptions.tsv", 'r', encoding="latin-1", errors="replace")

    #### Have a dict for items already inserted so that we don't insert them twice
    #### Prefill it with some abbreviations that are too common and we don't want
    namesDict = { "IS": 1 }

    for line in fh.readlines():
      columns = line.strip("\n").split("\t")
      curie = columns[0]
      name = columns[1]
      type = columns[2]

      names = [ name ]

      if re.match("OMIM:",curie):
        multipleNames = name.split("; ")
        if len(multipleNames) > 1:
          for possibleName in multipleNames:
            if possibleName == multipleNames[0]:
              next
            names.append(possibleName)

      elif re.match("R-HSA-",curie):
        #### Also store the path name without embedded abbreviations
        if re.search(r' \([A-Z0-9]{1,8}\)',name):
          newName = re.sub(r' \([A-Z0-9]{1,8}\)',"",name,flags=re.IGNORECASE)
          names.append(newName)

      #### If this is a UniProt identifier, also add the CURIE and the naked identifier without the prefix
      elif re.match("UniProtKB:[A-Z][A-Z0-9]{5}",curie) or re.match("UniProtKB:A[A-Z0-9]{9}",curie):
        tmp = re.sub("UniProtKB:","",curie)
        names.append(tmp)


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
      for name in names:
        name = name.upper()
        if name in namesDict and namesDict[name] == curie: continue

        #### Hard-coded list of short abbreviations to ignore because they're also English
        if name == "IS": continue
        if name == "AS": continue

        #print(type+" "+curie+"="+name)
        kgnode = KGNode(curie=curie,name=name,type=type)
        session.add(kgnode)
        namesDict[name] = curie

      ##### Try also adding in the curie as a resolvable name
      if curie not in namesDict:
        kgnode = KGNode(curie=curie,name=curie,type=type)
        session.add(kgnode)
        namesDict[curie] = curie


      #### Commit every now and then
      if int(lineCounter/1000) == lineCounter/1000:
        session.commit()
        print(str(lineCounter)+"..",end='',flush=True)

      lineCounter += 1

      #### Throttle the system for testing
      #if lineCounter > 100: break

    fh.close()
    session.flush()
    session.commit()
    print("")


  def createIndex(self):
    self.connect()
    engine = self.engine
    #engine.execute("DROP INDEX idx_name ON kgnode" + TESTSUFFIX)
    #engine.execute("CREATE INDEX idx_name ON kgnode"+TESTSUFFIX+"(name)")


  def get_curies(self,name):
    #### Ensure that we are connected
    self.connect()
    session = self.session

    #### First check to see if this is a curie. And if so, just return it
    #### oops, don't do this. it takes twice as long! Better to put them all in the index and do one query
    #if self.is_curie_present(name):
    #  return([name])

    #### Try to find the curie
    try:
      matches = session.query(KGNode).filter(KGNode.name==name.upper()).all()
    except:
      session.rollback()
      raise

    if matches is None: return None

    #### Return a list of curies
    curies = []
    for match in matches:
      curies.append(match.curie)
    return(curies)


  def is_curie_present(self,curie):
    #### Ensure that we are connected
    self.connect()
    session = self.session

    #### Try to find the curie
    try:
      match = session.query(KGNode).filter(KGNode.curie==curie).first()
    except:
      session.rollback()
      raise

    if match is None: return(False)
    return(True)


####################################################################################################
def main():
  parser = argparse.ArgumentParser(description="Tests or rebuilds the KG Node Index",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('-b', '--build', action="store_true", help="If set, (re)build the index from scratch", default=False)
  parser.add_argument('-t', '--test', action="store_true", help="If set, run a test of the index by doing several lookups", default=False)
  args = parser.parse_args()

  if not args.build and not args.test:
    parser.print_help()
    sys.exit(2)


  kgNodeIndex = KGNodeIndex()

  #### To (re)build
  if args.build:
    kgNodeIndex.createDatabase()
    kgNodeIndex.createNodeTable()
    #kgNodeIndex.createIndex()

  #### Exit here if tests are not requested
  if not args.test: sys.exit(0)


  print("==== Testing for finding curies by name ====")
  tests = [ "APS2", "phenylketonuria","Gaucher's disease","Gauchers disease","Gaucher disease",
    "Alzheimer Disease","Alzheimers disease","Alzheimer's Disease","kidney","KIDney","P06865","HEXA",
    "UniProtKB:P12004","rickets","fanconi anemia","retina","is" ]

  #### The first one takes a bit longer, so do one before starting the timer
  test = kgNodeIndex.get_curies("ibuprofen")

  t0 = timeit.default_timer()
  for test in tests:
    curies = kgNodeIndex.get_curies(test)
    print(test+" = "+str(curies))
  t1 = timeit.default_timer()
  print("Elapsed time: "+str(t1-t0))


  print("==== Testing presence of CURIEs ============================")
  tests = [ "REACT:R-HSA-2160456", "DOID:9281", "OMIM:261600", "DOID:1926xx", "HP:0002511", "UBERON:0002113", "UniProtKB:P06865", "P06865", "KEGG:C10399", "GO:0034187", "DOID:10652xx" ]

  t0 = timeit.default_timer()
  for test in tests:
    is_present = kgNodeIndex.is_curie_present(test)
    print(test+" = "+str(is_present))
  t1 = timeit.default_timer()
  print("Elapsed time: "+str(t1-t0))


####################################################################################################
if __name__ == "__main__":
  main()

