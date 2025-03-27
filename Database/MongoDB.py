import pymongo
import sys
from dotenv import load_dotenv
import os


# Handle all mongo fucntions

# teams
#       week1
#           kicks[{type, start{x,y}, end{x,y}, kicker}]
#           linebreaks[{location{x,y}, player, phase}]
#           mauls[location{x,y}, metersGained, tryScored?]


class Mongo():
    load_dotenv()

    client = pymongo.MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
    db = client.weeklyData
    collection = db["teams"]
    def __init__(self):
        pass
    def addDocument(self, obj):
        self.collection.insert_one(obj)

    def updateDoc(self, obj):
        pass

    def getLeagueAvg(self):
        pass

    def getTeamAvg(self, team):
        pass


def main():

    test = Mongo()
    test.addDocument({"name": "elotes"})

if __name__ == "__main__":
    main()