from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def addDocument(self, obj):
        pass

    @abstractmethod
    def updateDoc(self, obj):
        pass

    @abstractmethod
    def getLeagueAvg(self):
        pass

    @abstractmethod
    def getTeamAvg(self, team):
        pass
