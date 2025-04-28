# Graph Databases Using Neo4j and Amazon SNAP Dataset

The objective of this project is to process large graphs using a graph database. The core tasks include:

i. Install any graph processing system, Neo4j  
ii. Load a large graph from the Stanford SNAP large graph repository.  
iii. Provide an interface to run simple graph queries.  
iv. Profile and evaluate the performance of the system.

## Setting up the environment
It is recommended to use a virtual/conda environment setup and after setting up the environment, run `pip install -r requirements.txt` to install all the required dependencies

## Downloading and Parsing the Dataset

Download the dataset from [here](https://snap.stanford.edu/data/#amazon)

After you download the dataset we need to parse it ro appropriate csv files, to do this run all the codes in the `Parsing Codes` folder of the repository

## Setting Up Things

Install the `Neo4j Desktop`, you can refer to the [video](https://youtu.be/8jNPelugC2s?si=-PlJr_6oX9QjB5_L) for a tutorial and a Neo4j Desktop crash course.

After you successfully setup the Neo4j Desktop, then you need to setup the `APOC` on the database you are using, also you need to change the `config.py`, to make sure to connect to the correct database.

After you complete the setup, run all the codes in the `Create Database` folder of the repository.

After this you are good to go ...

## Starting the Server Locally

To start the server of this project run (before this make sure you have an active environment, if created)

```bash
  python run.py
```

Then on the browser run the 
```bash
localhost:9000
```
