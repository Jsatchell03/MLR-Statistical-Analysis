from MongoDB import Mongo
from lxml import etree
import re
import argparse
from pathlib import Path

# Pull weekly data and parse weelky packages
# Should be able to pull stats with CLA
# Heavy usage of command line parsing
#          kicks[{type, xStart, yStart, xEnd, yEnd, kicker}]
#           linebreaks[{location{x,y}, player, phase}]
#           mauls[location{x,y}, metersGained, tryScored?]

# kicks, linebreaks, and mauls are arrays with 2 elements 0 is home team stats and 1 is away.
# this should match up with the teams array eg. teams(home, away)

class StatExtractor:
    fieldLength = 140
    fieldWidth = 68
    tryZone = 20
    halfwayLine = fieldLength / 2
    

    def __init__(self, xmlFile):
        self.kicks = [[], []]
        self.linebreaks = [[], []]
        self.mauls = [[], []]
        self.xmlFile = xmlFile
        self.teams = self.getTeamNames()
        print(self.teams)

    def getAll(self):
        return self.getKicks(), self.getLinebreaks(), self.getMauls()

    def getKicks(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeKicks = root.xpath(f"//instance[code='{self.teams[0]} Kick']")
        awayKicks = root.xpath(f"//instance[code='{self.teams[1]} Kick']")
        for instance in homeKicks:
            kick = {}
            descriptor = str(instance.xpath("label[group='Kick Descriptor']/text/text()")[0])
            if descriptor == "Touch Kick":
                continue
            kick["kicker"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            kick["xStart"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            kick["yStart"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])
            kick["xEnd"] = float(instance.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
            kick["yEnd"] = self.fieldWidth - float(instance.xpath("label[group='Y_End']/text/text()")[0])
            kickStyle = str(instance.xpath("label[group='Kick Style']/text/text()")[0])
            if kickStyle == "Box":
                kick["type"] = "windy"
            else:
                match descriptor:
                    # Pocket
                    case  "Territorial":
                        kick["type"] = "pocket"
                    # Ice
                    case "Low":
                        kick["type"] = "ice"
                    # Snow
                    case "Bomb":
                        kick["type"] = "snow"
                    # Wedge
                    case "Chip":
                        kick["type"] = "wedge"
                    # Kick Pass
                    case "Cross Pitch":
                        kick["type"] = "kp"
            self.kicks[0].append(kick)
        for instance in awayKicks:
            kick = {}
            descriptor = str(instance.xpath("label[group='Kick Descriptor']/text/text()")[0])
            if descriptor == "Touch Kick":
                continue
            kick["kicker"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            kick["xStart"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            kick["yStart"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])
            kick["xEnd"] = float(instance.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
            kick["yEnd"] = self.fieldWidth - float(instance.xpath("label[group='Y_End']/text/text()")[0])
            kickStyle = str(instance.xpath("label[group='Kick Style']/text/text()")[0])
            if kickStyle == "Box":
                kick["type"] = "windy"
            else:
                match descriptor:
                    # Pocket
                    case  "Territorial":
                        kick["type"] = "pocket"
                    # Ice
                    case "Low":
                        kick["type"] = "ice"
                    # Snow
                    case "Bomb":
                        kick["type"] = "snow"
                    # Wedge
                    case "Chip":
                        kick["type"] = "wedge"
                    # Kick Pass
                    case "Cross Pitch":
                        kick["type"] = "kp"
            self.kicks[1].append(kick)
        return self.kicks

    def getLinebreaks(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeLinebreaks = root.xpath(
            f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teams[0]}' and group='Attacking Quality']]"
        )
        awayLinebreaks = root.xpath(
            f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teams[1]}' and group='Attacking Quality']]"
        )
        for instance in homeLinebreaks:
            linebreak = {}
            linebreak["x"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            linebreak["y"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])   
            linebreak["phase"] = instance.xpath("label[group='Phase Number'][position()=1]/text/text()")[0]  
            linebreak["player"] = str(instance.xpath("label[group='Player'][position()=1]/text/text()")[0]) 
            self.linebreaks[0].append(linebreak)

        for instance in awayLinebreaks:
            linebreak = {}
            linebreak["x"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            linebreak["y"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])   
            linebreak["phase"] = instance.xpath("label[group='Phase Number'][position()=1]/text/text()")[0]  
            linebreak["player"] = str(instance.xpath("label[group='Player'][position()=1]/text/text()")[0]) 
            self.linebreaks[1].append(linebreak)

        return self.linebreaks
    
    def getMauls(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeMauls = root.xpath(
            f"//instance[code='{self.teams[0]} Maul']"
        )
        awayMauls = root.xpath(
            f"//instance[code='{self.teams[1]} Maul']"
        )
        for instance in homeMauls:
            maul = {}
            maul["x"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            maul["y"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])
            maulOutcome = str(instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0])
            maul["tryScored"] = (maulOutcome == "Try Scored")
            maul["metersGained"] = int(instance.xpath("label[group='Maul Metres']/text/text()")[0])
            self.mauls[0].append(maul)

        for instance in awayMauls:
            maul = {}
            maul["x"] = float(instance.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
            maul["y"] = self.fieldWidth - float(instance.xpath("label[group='Y_Start']/text/text()")[0])
            maulOutcome = str(instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0])
            maul["tryScored"] = (maulOutcome == "Try Scored")
            maul["metersGained"] = int(instance.xpath("label[group='Maul Metres']/text/text()")[0])
            self.mauls[1].append(maul)

        return self.mauls

# Get all restart kicks and recpetions loop through until you pull both team names
    def getTeamNames(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()

        restartKicks = root.xpath("//instance[contains(code, 'Restart Kick')]")
        restartReceptions = root.xpath("//instance[contains(code, 'Restart Reception')]")
        teams = []

        for i in range(max(len(restartKicks), len(restartReceptions))):
            if len(teams) >= 2:
                break
            kickTeam = str(restartKicks[i].xpath("code/text()")[0]).split(" ")[:-2]
            kickTeam = " ".join(kickTeam)
            receiveTeam = str(restartReceptions[i].xpath("code/text()")[0]).split(" ")[:-2]
            receiveTeam = " ".join(receiveTeam)
            if kickTeam not in teams:
                teams.append(kickTeam)
            if receiveTeam not in teams:
                teams.append(receiveTeam)

        return teams

def main():
    parser = argparse.ArgumentParser(description="Process Weekly XML files in a directory")
    parser.add_argument("folder", help="Path to folder containing XML files")
    parser.add_argument("week", help="Week these files reference")
    
    args = parser.parse_args()
    dir = Path(args.folder)
    files = list(dir.glob("*.xml"))
    week = int(args.week)

    db = Mongo()

    for file in files:
        extractor = StatExtractor(str(file))
        teams = extractor.teams
        kicks = extractor.getKicks()
        linebreaks = extractor.getLinebreaks()
        mauls = extractor.getMauls()
        for i in range(len(teams)):
            doc = {"week": week}
            doc["kicks"] = kicks[i]
            doc["linebreaks"] = linebreaks[i]
            doc["mauls"] = mauls[i]
            db.addWeek(teams[i], doc)



# Clear WEEK 1 from DB


if __name__ == "__main__":
    main()
