import pymongo
import sys
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId


# Handle all mongo fucntions

# teams {
#    chicagoHounds: {2025:[{kicks, linebreaks, mauls}, by week], 2026:[]}
# }
#   2025
#       week1
#          kicks[{type, start{x,y}, end{x,y}, kicker}]
#           linebreaks[{location{x,y}, player, phase}]
#           mauls[location{x,y}, metersGained, tryScored?]


class Mongo:
    teams = {
        "NOLA Gold": "67e6db38d22ceb3af28c85f9",
        "Anthem RC": "67ee9bc85adc43f633a6622e",
        "Chicago Hounds": "67ee9c025adc43f633a6622f",
        "Houston SaberCats": "67ee9c1e5adc43f633a66230",
        "Miami Sharks": "67ee9c415adc43f633a66231",
        "New England Free Jacks": "67ee9c5c5adc43f633a66232",
        "Old Glory DC": "67ee9c995adc43f633a66233",
        "RFCLA": "67ee9cb55adc43f633a66234",
        "San Diego Legion": "67ee9cf15adc43f633a66235",
        "Seattle Seawolves": "67ee9d025adc43f633a66236",
        "Utah Warriors": "67ee9d265adc43f633a66237",
    }

    load_dotenv()

    client = pymongo.MongoClient(os.getenv("MONGO_CONNECTION_STRING"))
    db = client.weeklyData
    teamsCol = db["teams"]

    def __init__(self):
        pass

    def addWeek(self, team, obj):
        self.teamsCol.update_one(
            {"_id": ObjectId(self.teams[team])}, {"$push": {"weeks": obj}}
        )

    def updateDoc(self, obj):
        pass

    def getAllWeeks(self, team):
        pass

    def getLast3Weeks(self, team):
        pass


def main():

    test = Mongo()
    test.addDocument({"name": "elotes"})


if __name__ == "__main__":
    main()
