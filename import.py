import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Set up database
#engine = create_engine(os.getenv("DATABASE_URL"))
engine = create_engine("postgres://sjuqziiecivtcn:9eaff364ca2e154671da652d9d6cecf7e4d1cae777517e3f64ab4360a09d3dff@ec2-107-20-243-220.compute-1.amazonaws.com:5432/df8s1rv3i2dqi")
db = scoped_session(sessionmaker(bind=engine))

def main():
    # open books.csv file
    f = open("books.csv")
    reader = csv.reader(f)
    # used to keep track which is col names
    col = True

    # create database
    db.execute('''CREATE TABLE books (isbn varchar, title varchar, author varchar, year int);''')
    for isbn, title, author, year in reader:
        # use to skip first row b/c those contain col names
        if not col:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", 
                        {"isbn": isbn, "title": title, "author": author, "year": year})
        #print (isbn, title, author, year)
        col = False
    db.commit()

if __name__ == "__main__":
    main()
