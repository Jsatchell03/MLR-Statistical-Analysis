from lxml import etree
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import argparse
import statistics
import matplotlib.image as mpimg
import matplotlib.ticker as tck
from operator import itemgetter
from collections import OrderedDict
from pptx import Presentation
from pptx.util import Inches


# Stat extractor will pull all the data that we are uplading to mongoDb. With
# this data we should be able to calculate all of the stats we get currently.
# If StatMonkey is in pres mode run full StatExtractor and save the data to an atribute

#          kicks[{type, start{x,y}, end{x,y}, kicker}]
#           linebreaks[{location{x,y}, player, phase}]
#           mauls[location{x,y}, metersGained, tryScored?]

class StatExtractor:
    kicks = []
    linebreaks = []
    mauls = []

    def __init__(self, xmlFiles, teamName):
        self.xmlFiles = xmlFiles
        self.teamName = teamName

    def getAll(self):
        pass
    
    def getKicks(self):
        pass

    def getLinebreaks(self):
        pass

    def getMauls(self):
        pass

class StatMonkey:
    fieldLength = 140
    fieldWidth = 68
    tryZone = 20
    halfwayLine = fieldLength / 2
    figWidth = 11
    figHeight = 6
    arrowWidth = 1.5
    linebreakKeyPlayers = []
    mainKickers = []


    def __init__(self, xmlFiles, teamName, mode="presentation"):
        self.xmlFiles = xmlFiles
        self.teamName = teamName
        self.mode = mode
        if mode == "presentation":
            self.prs = Presentation()


    def show(self, statPath):
        plt.figure(figsize=(self.figWidth, self.figHeight)) 
        img = mpimg.imread(statPath)
        plt.imshow(img)
        plt.axis('off') 
        plt.tight_layout()
        plt.show()
        plt.close()

    def getAllStats(self):
        results = []
        if self.mode == "presentation":
            results.append(self.getKickStats())
            results.append(self.getKickPaths())
            results.append(self.getAttackingKickPaths())
            results.append(self.getGroupKickPaths("pocket"))
            results.append(self.getGroupKickPaths("windy"))
            results.append(self.getGroupKickPaths("ice"))
            results.append(self.getGroupKickPaths("snow"))
            results.append(self.getGroupKickPaths("wedge"))
            results.append(self.getGroupKickPaths("kp"))
            for player in self.mainKickers:
                results.append(self.getPlayerKickPaths(player))
            results.append(self.getLinebreakCountByPlayer())
            results.append(self.getLinebreakPhases())
            results.append(self.getLinebreakLocations())
            for player in self.linebreakKeyPlayers:
                results.append(self.getLinebreakLocationsByPlayer(player))
            results.append(self.getMaulMap())
        return(results)

# Optional param for mongo objects

    def getKickStats(self):
        plt.figure(figsize=(self.figWidth, self.figHeight))
        playerKicks = {}
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                kicks = root.xpath(f"//instance[code='{self.teamName} Kick']")
                for kick in kicks:
                    player = str(
                        kick.xpath("label[group='Player'][position()=1]/text/text()")[0]
                    )
                    meters = int(
                        kick.xpath("label[group='Kick Metres'][position()=1]/text/text()")[
                            0
                        ]
                    )
                    if player in playerKicks:
                        playerKicks[player] = playerKicks[player] + 1
                    else:
                        playerKicks[player] = 1

            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        median = statistics.median(playerKicks.values())
        for player in playerKicks:
            if playerKicks[player] > median:
                self.mainKickers.append(player)
        sortedPlayerKicks = OrderedDict(sorted(playerKicks.items(), key=itemgetter(1), reverse=True))
        plt.title(f"Number Of Kicks By Player")  
        plt.bar(sortedPlayerKicks.keys(), sortedPlayerKicks.values())
        plt.ylabel("Number of Breaks")
        plt.xticks(rotation=45)  
        plt.tight_layout() 
        plt.subplots_adjust(bottom=0.25)  
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Kick_Count_By_Player.png"
        plt.savefig(path)
        plt.close()
        if self.mode == "database":
            return 
        else:
            return path
    
    def addAllStatsToPres(self, statPathArray):
        for stat in statPathArray:
            self.addStatToPres(stat) 

    def make22Graph(self):
        plt.figure(figsize=(self.figWidth, self.figHeight))
    
        plt.xlim(0, 15)
        plt.ylim(0, 15)
        
        entries = self.get22Entries()
        ruckSpeed = self.get22RuckSpeed()
        plt.text(2, 5, f"Points Per 22 Entry: {entries}", fontsize=24, color='black')
        plt.text(2, 10, f"Ruck Speed In 22: {ruckSpeed}", fontsize=24, color='black')
        
        plt.axis('off')
        
        path = f"Stat PNGs/{self.teamName.replace(' ', '_')}_22_Stats.png"
        
        # Save and close
        plt.savefig(path)
        plt.close()
        
        return path
        
    def getLinebreakLocations(self):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        xValues = []
        yValues = []
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                linebreaks = root.xpath(
                    f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teamName}' and group='Attacking Quality']]"
                )
                for linebreak in linebreaks:
                    xStart = float(linebreak.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(linebreak.xpath("label[group='Y_Start']/text/text()")[0])
                    xValues.append(xStart)
                    yValues.append(yStart)       
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        ax.scatter(xValues, yValues) 
        plt.title('Linebreak Locations')
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Linebreak_Locations.png"
        plt.savefig(path)
        return path
    
    def getLinebreakLocationsByPlayer(self, player):

        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        xValues = []
        yValues = []
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                linebreaks = root.xpath(
                    f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teamName}' and group='Attacking Quality']]"
                )
                for linebreak in linebreaks:
                    playerName = str(
                        linebreak.xpath(
                            "label[group='Player'][position()=1]/text/text()"
                        )[0]
                    )
                    if player == playerName:
                        xStart = float(linebreak.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                        yStart = self.fieldWidth - float(linebreak.xpath("label[group='Y_Start']/text/text()")[0])
                        xValues.append(xStart)
                        yValues.append(yStart)       
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        ax.scatter(xValues, yValues) 
        plt.title(f'{player} Linebreak Locations')
        path = f"Stat PNGs/{player.replace(" ", "_")}_Linebreak_Locations.png"
        plt.savefig(path)
        return path

    def get22Entries(self):
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                entries = root.xpath(
                    f"//instance[code='{self.teamName} 22 Entry' and label[text='New Entry' and group='22 Entry']]"
                )
                trys = root.xpath(
                    f"//instance[code='{self.teamName} Try']"
                )    
                penKicks = root.xpath(
                    f"//instance[label[text='Penalty Goal' and group='Goal Type'] and label[text='True' and group='Attempt from 22 Visit'] and label[text='{self.teamName}' and group='Goal Kick']]"
                )       
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        pointsPerEntry = ((len(trys) * 5) + (3 * len(penKicks))) / len(entries)
        return round(pointsPerEntry, 2)

    def get22RuckSpeed(self):
        # not done
        # self.fieldLength - 42
        ruckSpeeds = []
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                rucks = root.xpath(
                    f"//instance[code='{self.teamName} Ruck']"
                )
                for ruck in rucks:
                    xStart = float(ruck.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    if xStart < self.fieldLength - 42:
                        continue
                    xStart = float(ruck.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    ruckSpeed = int(str(ruck.xpath("label[group='Ruck Speed']/text/text()")[0])[0])
                    ruckSpeeds.append(ruckSpeed)
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        return round(statistics.mean(ruckSpeeds), 2)

    def drawRugbyPitch(self, ax):
        # Draw halfway line
        ax.plot([self.halfwayLine, self.halfwayLine], [0, self.fieldWidth], color='black', linestyle='-')
        # Draw Channels
        ax.plot([self.halfwayLine - 2.5, self.halfwayLine + 2.5],[self.fieldWidth - 5, self.fieldWidth - 5],color="black", linestyle="-" )
        ax.plot([self.halfwayLine - 2.5, self.halfwayLine + 2.5],[self.fieldWidth - 15, self.fieldWidth - 15],color="black", linestyle="-" )
        ax.plot([self.halfwayLine - 2.5, self.halfwayLine + 2.5],[15, 15],color="black", linestyle="-" )
        ax.plot([self.halfwayLine - 2.5, self.halfwayLine + 2.5],[5, 5],color="black", linestyle="-" )

        # Draw 10-meter lines

        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [5 - 2.5, 5 + 2.5], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [5 - 2.5, 5 + 2.5], color='black', linestyle='-')
        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [15 - 2.5, 15 + 2.5], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [15 - 2.5, 15 + 2.5], color='black', linestyle='-')

        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [self.fieldWidth - (5 - 2.5), self.fieldWidth - (5 + 2.5)], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [self.fieldWidth - (5 - 2.5), self.fieldWidth - (5 + 2.5)], color='black', linestyle='-')
        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [self.fieldWidth - (15 - 2.5), self.fieldWidth - (15 + 2.5)], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [self.fieldWidth - (15 - 2.5), self.fieldWidth - (15 + 2.5)], color='black', linestyle='-')


        # Creating mid 3 dashes for 10 meter line
        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [self.fieldWidth/2 - 2.5, self.fieldWidth/2 + 2.5], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [self.fieldWidth/2 - 2.5, self.fieldWidth/2 + 2.5], color='black', linestyle='-')

        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [self.fieldWidth/2 - 11.83, self.fieldWidth/2 - 6.83], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [self.fieldWidth/2 - 11.83, self.fieldWidth/2 - 6.83], color='black', linestyle='-')

        ax.plot([self.halfwayLine + 10, self.halfwayLine + 10], [self.fieldWidth/2 + 11.83, self.fieldWidth/2 + 6.83], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 10, self.halfwayLine - 10], [self.fieldWidth/2 + 11.83, self.fieldWidth/2 + 6.83], color='black', linestyle='-')
        # Draw Chanels
        ax.plot([self.halfwayLine + 7.5, self.halfwayLine + 12.5], [5, 5], color='black', linestyle='-')
        ax.plot([self.halfwayLine + 7.5, self.halfwayLine + 12.5], [15, 15], color='black', linestyle='-')
        ax.plot([self.halfwayLine + 7.5, self.halfwayLine + 12.5], [self.fieldWidth - 5, self.fieldWidth - 5], color='black', linestyle='-')
        ax.plot([self.halfwayLine + 7.5, self.halfwayLine + 12.5], [self.fieldWidth - 15, self.fieldWidth - 15], color='black', linestyle='-')

        ax.plot([self.halfwayLine - 7.5, self.halfwayLine - 12.5], [5, 5], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 7.5, self.halfwayLine - 12.5], [15, 15], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 7.5, self.halfwayLine - 12.5], [self.fieldWidth - 5, self.fieldWidth - 5], color='black', linestyle='-')
        ax.plot([self.halfwayLine - 7.5, self.halfwayLine - 12.5], [self.fieldWidth - 15, self.fieldWidth - 15], color='black', linestyle='-')

        # Draw 22-meter lines
        ax.plot([42, 42 ], [0, self.fieldWidth], color='black')
        ax.plot([self.fieldLength - 42, self.fieldLength - 42], [0, self.fieldWidth], color='black')
        # Draw Chanels
        ax.plot([42 - 2.5, 42 + 2.5],[self.fieldWidth - 5, self.fieldWidth - 5],color="black", linestyle="-" )
        ax.plot([42 - 2.5, 42 + 2.5],[self.fieldWidth - 15, self.fieldWidth - 15],color="black", linestyle="-" )
        ax.plot([42 - 2.5, 42 + 2.5],[15, 15],color="black", linestyle="-" )
        ax.plot([42 - 2.5, 42 + 2.5],[5, 5],color="black", linestyle="-" )

        ax.plot([(self.fieldLength - 42) - 2.5, (self.fieldLength - 42) + 2.5],[self.fieldWidth - 5, self.fieldWidth - 5],color="black", linestyle="-" )
        ax.plot([(self.fieldLength - 42) - 2.5, (self.fieldLength - 42) + 2.5],[self.fieldWidth - 15, self.fieldWidth - 15],color="black", linestyle="-" )
        ax.plot([(self.fieldLength - 42) - 2.5, (self.fieldLength - 42) + 2.5],[15, 15],color="black", linestyle="-" )
        ax.plot([(self.fieldLength - 42) - 2.5, (self.fieldLength - 42) + 2.5],[5, 5],color="black", linestyle="-" )
        # Draw goal lines
        ax.plot([self.tryZone, self.tryZone], [0, self.fieldWidth], color='black', linewidth=3)
        ax.plot([self.fieldLength - self.tryZone, self.fieldLength - self.tryZone], [0, self.fieldWidth], color='black', linewidth=3)

        # Draw the field rectangle
        ax.plot([0, self.fieldLength], [0, 0], color='green', linewidth=3)
        ax.plot([0, self.fieldLength], [self.fieldWidth, self.fieldWidth], color='green', linewidth=3)
        ax.plot([0, 0], [0, self.fieldWidth], color='green', linewidth=3)
        ax.plot([self.fieldLength, self.fieldLength], [0, self.fieldWidth], color='green', linewidth=3)

        ax.text(self.tryZone/2, self.fieldWidth/2, self.teamName,
                rotation=-90,
                ha='center',
                va='center',
                fontsize=12)
        
        # Right try zone
        ax.text(self.fieldLength - self.tryZone/2, self.fieldWidth/2, 'Opposition',
                rotation=90,
                ha='center',
                va='center',
                fontsize=12)

           # Set limits and aspect ratio
        ax.set_xlim(-5, self.fieldLength + 5)
        ax.set_ylim(-5, self.fieldWidth + 5)
        ax.set_aspect('equal', adjustable='box')

        # Remove axes ticks and labels
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout(pad=2.5)

    def drawHalfPitch(self, ax):
        halfFieldLength = 140
        halfTryZone = 40
        # Draw the field rectangle
        ax.plot([0, halfFieldLength], [0, 0], color='green', linewidth=3)
        ax.plot([0, halfFieldLength], [self.fieldWidth, self.fieldWidth], color='green', linewidth=3)
        ax.plot([0, 0], [0, self.fieldWidth], color='green', linewidth=3)
        ax.plot([halfFieldLength, halfFieldLength], [0, self.fieldWidth], color='green', linewidth=3)
        # Draw 10-meter lines
        ax.plot([20, 20], [5 - 2.5, 5 + 2.5], color='black', linestyle='-')
        ax.plot([20, 20], [15 - 2.5, 15 + 2.5], color='black', linestyle='-')

        ax.plot([20, 20], [self.fieldWidth - (5 - 2.5), self.fieldWidth - (5 + 2.5)], color='black', linestyle='-')
        ax.plot([20, 20], [self.fieldWidth - (15 - 2.5), self.fieldWidth - (15 + 2.5)], color='black', linestyle='-')


        # Creating mid 3 dashes for 10 meter line
        ax.plot([20, 20], [self.fieldWidth/2 - 2.5, self.fieldWidth/2 + 2.5], color='black', linestyle='-')
        ax.plot([20, 20], [self.fieldWidth/2 - 11.83, self.fieldWidth/2 - 6.83], color='black', linestyle='-')
        ax.plot([20, 20], [self.fieldWidth/2 + 11.83, self.fieldWidth/2 + 6.83], color='black', linestyle='-')
        # Draw Chanels
        ax.plot([10 + 5, 10 + 15], [5, 5], color='black', linestyle='-')
        ax.plot([10 + 5, 10 + 15], [15, 15], color='black', linestyle='-')
        ax.plot([10 + 5, 10 + 15], [self.fieldWidth - 5, self.fieldWidth - 5], color='black', linestyle='-')
        ax.plot([10 + 5, 10 + 15], [self.fieldWidth - 15, self.fieldWidth - 15], color='black', linestyle='-')

        # Draw 22-meter lines
        ax.plot([56, 56], [0, self.fieldWidth], color='black')
        # Draw Chanels
        ax.plot([(56) - 5, (56) + 5],[self.fieldWidth - 5, self.fieldWidth - 5],color="black", linestyle="-" )
        ax.plot([(56) - 5, (56) + 5],[self.fieldWidth - 15, self.fieldWidth - 15],color="black", linestyle="-" )
        ax.plot([(56) - 5, (56) + 5],[15, 15],color="black", linestyle="-" )
        ax.plot([(56) - 5, (56) + 5],[5, 5],color="black", linestyle="-" )
        # Draw goal lines
        ax.plot([100, 100], [0, self.fieldWidth], color='black', linewidth=3)
        
        # Right try zone
        ax.text(halfFieldLength - halfTryZone/2, self.fieldWidth/2, 'Opposition',
                rotation=90,
                ha='center',
                va='center',
                fontsize=12)

        # Set limits and aspect ratio
        ax.set_xlim(-5, halfFieldLength + 5)
        ax.set_ylim(-5, self.fieldWidth + 5)
        ax.set_aspect('equal', adjustable='box')

        # Remove axes ticks and labels
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout(pad=2.5)

    def addStatToPres(self, statImgPath):
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.prs.slide_width = Inches(16)
        self.prs.slide_height = Inches(9)

        left = top = Inches(0)
        width = self.prs.slide_width
        height = self.prs.slide_height
        slide.shapes.add_picture("assets/bg.png", left, top, width, height)

        top = Inches(1.5)
        left  = Inches(2.5)
        slide.shapes.add_picture(statImgPath, left, top)

        top = Inches(0)
        left  = Inches(0)
        width = height = Inches(1.5)
        slide.shapes.add_picture("assets/HoundsBadge_LightOnDarkBG.png", left, top, width, height)

        if self.teamName != "Chicago Hounds":
            top = Inches(0)
            left  = Inches(2)
            width = height = Inches(1)
            slide.shapes.add_picture(f"assets/League Logos/{self.teamName.replace(' ', "_")}.png", left, top, width, height)

        top = Inches(7.25)
        left  = Inches(14.5)
        width = height = Inches(1.5)
        slide.shapes.add_picture("assets/HoundsShield_LightOnDarkBG.png", left, top, width, height)
        
        self.prs.save(f"{self.teamName}.pptx")

    def getMaulMap(self):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        xValues = []
        yValues = []
        maulMetersArr = []
        trueMaulMetersArr = []
        colors = []
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                mauls = root.xpath(
                    f"//instance[code='{self.teamName} Maul']"
                )
                for maul in mauls:
                    xStart = float(maul.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(maul.xpath("label[group='Y_Start']/text/text()")[0])
                    maulOutcome = str(maul.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0])
                    if maulOutcome == "Try Scored":
                        maulMetersArr.append(int(999))
                    else:
                        maulMetersArr.append(int(maul.xpath("label[group='Maul Metres']/text/text()")[0]))
                    trueMaulMetersArr.append(int(maul.xpath("label[group='Maul Metres']/text/text()")[0]))
                    xValues.append(xStart)
                    yValues.append(yStart)       
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        avg = (sum(trueMaulMetersArr)) / (len(trueMaulMetersArr))
        for dist in maulMetersArr:
            if dist < avg:
                colors.append("#E15554")
            else:
                colors.append("#3BB273")
        ax.scatter(xValues, yValues, c= colors) 
        pos = mpatches.Patch(color="#3BB273", label=f'> {round(avg,1)} Meters Made/Try Scored')
        neg = mpatches.Patch(color="#E15554", label=f'< {round(avg,1)} Meters Made')
        plt.legend(handles=[pos, neg],loc="lower left")
        plt.title(f'Maul Locations ({round(avg, 1)} Meters Per Maul)')
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Mauls.png"
        plt.savefig(path)
        plt.close()
        return path
    
    def getLinebreakCountByPlayer(self):
        plt.figure(figsize=(self.figWidth, self.figHeight))
        playerBreaks = {}
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                linebreaks = root.xpath(
                    f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teamName}' and group='Attacking Quality']]"
                )
                
                for linebreak in linebreaks:
                    player = str(
                        linebreak.xpath(
                            "label[group='Player'][position()=1]/text/text()"
                        )[0]
                    )
                    
                    playerBreaks[player] = playerBreaks[player] + 1 if player in playerBreaks else 1

            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        for player in playerBreaks:
            if playerBreaks[player] > statistics.median(playerBreaks.values()):
                self.linebreakKeyPlayers.append(player)
        plt.title(f"Number Of Linebreaks By Player")   
        sortedPlayerBreaks = OrderedDict(sorted(playerBreaks.items(), key=itemgetter(1), reverse=True))
        plt.bar(sortedPlayerBreaks.keys(), sortedPlayerBreaks.values())
        plt.ylabel("Number of Breaks")
        plt.xticks(rotation=45)  
        plt.tight_layout() 
        plt.subplots_adjust(bottom=0.25) 
        plt.gca().yaxis.set_major_locator(tck.MultipleLocator(base=1))  # Using base=1 as an example
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Linebreak_Count_By_Player.png"
        plt.savefig(path)
        plt.close()
        return path
        
    def getLinebreakPhases(self):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        breakPhases = {}
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                linebreaks = root.xpath(
                    f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teamName}' and group='Attacking Quality']]"
                )
                
                for linebreak in linebreaks:
                    phase = linebreak.xpath(
                            "label[group='Phase Number'][position()=1]/text/text()"
                        )[0]
                    breakPhases[phase] = breakPhases[phase] + 1 if phase in breakPhases else 1

            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")

        plt.title(f"Phase Of Linebreaks")

        breakPhasesKeys = list(breakPhases.keys())
        breakPhasesKeys.sort()
        sortedBreakPhases = {i: breakPhases[i] for i in breakPhasesKeys}

        ax.bar(sortedBreakPhases.keys(), sortedBreakPhases.values())
        ax.set_ylabel("Number of Breaks")
        ax.tick_params(axis="x", rotation=45)
        ax.set_aspect('equal', adjustable='box')
        ax.yaxis.set_major_locator(tck.MultipleLocator())
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Linebreak_Phases.png"
        plt.savefig(path)
        plt.close()
        return path

    def getKickPaths(self):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        total = 0
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                kicks = root.xpath(f"//instance[code='{self.teamName} Kick']")
                for kick in kicks:
                    xStart = float(kick.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(kick.xpath("label[group='Y_Start']/text/text()")[0])
                    xEnd = float(kick.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
                    yEnd = self.fieldWidth - float(kick.xpath("label[group='Y_End']/text/text()")[0])
                    descriptor = str(kick.xpath("label[group='Kick Descriptor']/text/text()")[0])
                    if descriptor == "Touch Kick":
                        continue
                    total += 1
                    kickStyle = str(kick.xpath("label[group='Kick Style']/text/text()")[0])
                    dx = xEnd - xStart
                    dy = yEnd - yStart
                    color = ""
                    # Windy
                    if kickStyle == "Box":
                        color = "#FF85B4"
                    else:
                        match descriptor:
                            # Pocket
                            case  "Territorial":
                                color = "#63AAE3"
                            # Ice
                            case "Low":
                                color = "#E15554"
                            # Snow
                            case "Bomb":
                                color = "#E1BC29"
                            # Wedge
                            case "Chip":
                                color = "#2E8A59"
                            # Kick Pass
                            case "Cross Pitch":
                                color = "#7768AE"
                    plt.arrow(xStart, yStart, dx, dy, 
                            head_width=2, head_length=1, 
                            fc=color, ec=color, lw=self.arrowWidth,
                            length_includes_head=True)
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        pocket = mpatches.Patch(color="#63AAE3", label='Pocket')
        windy =  mpatches.Patch(color="#FF85B4", label='Windy')
        ice = mpatches.Patch(color="#E15554", label='Ice')
        snow = mpatches.Patch(color="#E1BC29", label='Snow')
        wedge = mpatches.Patch(color="#2E8A59", label='Wedge')
        kp = mpatches.Patch(color="#7768AE", label='Kick Pass')
        plt.legend(handles=[pocket, windy, ice ,snow, wedge, kp],loc="lower left")
        plt.title(f'Kick Paths ({total} Total)')
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Kick_Paths.png"
        plt.savefig(path)
        plt.close()
        return path

    def getAttackingKickPaths(self):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawHalfPitch(ax)
        total = 0

        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                kicks = root.xpath(f"//instance[code='{self.teamName} Kick']")
                for kick in kicks:
                    xStart = float(kick.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(kick.xpath("label[group='Y_Start']/text/text()")[0])
                    xEnd = float(kick.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
                    yEnd = self.fieldWidth - float(kick.xpath("label[group='Y_End']/text/text()")[0])
                    descriptor = str(kick.xpath("label[group='Kick Descriptor']/text/text()")[0])
                    if descriptor == "Touch Kick":
                        continue
                    if xStart < 70:
                        continue
                    total += 1
                    xStart = (xStart - 70) * 2
                    xEnd = (xEnd - 70) * 2
                    kickStyle = str(kick.xpath("label[group='Kick Style']/text/text()")[0])
                    dx = xEnd - xStart
                    dy = yEnd - yStart
                    color = ""
                    # Windy
                    if kickStyle == "Box":
                        color = "#FF85B4"

                    else:
                        match descriptor:
                            # Pocket
                            case  "Territorial":
                                color = "#63AAE3"
                            # Ice
                            case "Low":
                                color = "#E15554"
                            # Snow
                            case "Bomb":
                                color = "#E1BC29"
                            # Wedge
                            case "Chip":
                                color = "#2E8A59"
                            # Kick Pass
                            case "Cross Pitch":
                                color = "#7768AE"
                    plt.arrow(xStart, yStart, dx, dy, 
                            head_width=2, head_length=1, 
                            fc=color, ec=color, lw=self.arrowWidth,
                            length_includes_head=True)
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        pocket = mpatches.Patch(color="#63AAE3", label='Pocket')
        windy =  mpatches.Patch(color="#FF85B4", label='Windy')
        ice = mpatches.Patch(color="#E15554", label='Ice')
        snow = mpatches.Patch(color="#E1BC29", label='Snow')
        wedge = mpatches.Patch(color="#2E8A59", label='Wedge')
        kp = mpatches.Patch(color="#7768AE", label='Kick Pass')
        plt.legend(handles=[pocket, windy, ice ,snow, wedge, kp],loc="lower left")
        plt.title(f'Attacking Kick Paths ({total} Total)')
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_Attacking_Kick_Paths.png"
        plt.savefig(path)
        plt.close()
        return path

    def getPlayerKickPaths(self, player):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        total = 0
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='{player}' and group='Player']]")
                for kick in kicks:
                    xStart = float(kick.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(kick.xpath("label[group='Y_Start']/text/text()")[0])
                    xEnd = float(kick.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
                    yEnd = self.fieldWidth - float(kick.xpath("label[group='Y_End']/text/text()")[0])
                    descriptor = str(kick.xpath("label[group='Kick Descriptor']/text/text()")[0])
                    if descriptor == "Touch Kick":
                        continue
                    total += 1
                    kickStyle = str(kick.xpath("label[group='Kick Style']/text/text()")[0])
                    dx = xEnd - xStart
                    dy = yEnd - yStart
                    color = ""
                    # Windy
                    if kickStyle == "Box":
                        color = "#FF85B4"
                    else:
                        match descriptor:
                            # Pocket
                            case  "Territorial":
                                color = "#63AAE3"
                            # Ice
                            case "Low":
                                color = "#E15554"
                            # Snow
                            case "Bomb":
                                color = "#E1BC29"
                            # Wedge
                            case "Chip":
                                color = "#2E8A59"
                            # Kick Pass
                            case "Cross Pitch":
                                color = "#7768AE"
                    plt.arrow(xStart, yStart, dx, dy, 
                            head_width=2, head_length=1, 
                            fc=color, ec=color,lw=self.arrowWidth,
                            length_includes_head=True)
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        pocket = mpatches.Patch(color="#63AAE3", label='Pocket')
        windy =  mpatches.Patch(color="#FF85B4", label='Windy')
        ice = mpatches.Patch(color="#E15554", label='Ice')
        snow = mpatches.Patch(color="#E1BC29", label='Snow')
        wedge = mpatches.Patch(color="#2E8A59", label='Wedge')
        kp = mpatches.Patch(color="#7768AE", label='Kick Pass')
        plt.legend(handles=[pocket, windy, ice ,snow, wedge, kp],loc="lower left")
        plt.title(f'{player} Kick Paths ({total} Total)')
        path = f"Stat PNGs/{player.replace(" ", "_")}_Kick_Paths.png"
        plt.savefig(path)
        plt.close()
        return path

    def getGroupKickPaths(self, type):
        fig, ax = plt.subplots(figsize=(self.figWidth, self.figHeight))
        self.drawRugbyPitch(ax)
        total = 0
        for xmlFile in self.xmlFiles:
            try:
                tree = etree.parse(str(xmlFile))
                root = tree.getroot()
                if type == "windy":
                    kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Box' and group='Kick Style'] and label[text!='Touch Kick' and group='Kick Descriptor']]")
                    color = "#FF85B4"
                    title = "Windy/Box"
                else:
                    match type:
                            # Pocket
                            case  "pocket":
                                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Territorial' and group='Kick Descriptor'] and label[text='Regular' and group='Kick Style']]")
                                color = "#4D9DE0"
                                title = "Pocket/Long"
                            # Ice
                            case "ice":
                                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Low' and group='Kick Descriptor']]")
                                color = "#E15554"
                                title = "Ice/Grubber"
                            # Snow
                            case "snow":
                                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Bomb' and group='Kick Descriptor']]")
                                color = "#E1BC29"
                                title = "Snow/Up And Under"
                            # Wedge
                            case "wedge":
                                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Chip' and group='Kick Descriptor']]")
                                color = "#3BB273"
                                title = "Wedge/Chip"
                            # Kick Pass
                            case "kp":
                                kicks = root.xpath(f"//instance[code='{self.teamName} Kick' and label[text='Cross Pitch' and group='Kick Descriptor']]")
                                color = "#7768AE"
                                title = "Kick Pass/Cross"
                for kick in kicks:
                    total += 1 
                    xStart = float(kick.xpath("label[group='X_Start']/text/text()")[0]) + self.tryZone
                    yStart = self.fieldWidth - float(kick.xpath("label[group='Y_Start']/text/text()")[0])
                    xEnd = float(kick.xpath("label[group='X_End']/text/text()")[0]) + self.tryZone
                    yEnd = self.fieldWidth - float(kick.xpath("label[group='Y_End']/text/text()")[0])
                    dx = xEnd - xStart
                    dy = yEnd - yStart
                    plt.arrow(xStart, yStart, dx, dy, 
                            head_width=2, head_length=1, 
                            fc=color, ec=color,lw=self.arrowWidth,
                            length_includes_head=True)
            except etree.XMLSyntaxError as e:
                print(f"Error parsing {xmlFile.name}: {e}")
        plt.title(f'{title} Kick Paths ({total} Total)')
        path = f"Stat PNGs/{self.teamName.replace(" ", "_")}_{type.capitalize()}_Kick_Paths.png"
        plt.savefig(path)
        plt.close()
        return path

def main():
    parser = argparse.ArgumentParser(description="Process XML files in a directory")
    parser.add_argument("folder", help="Path to folder containing XML files")
    parser.add_argument(
        "team",
        help="Team name spelt and capitalize the exact way it is referenced in Oval Insights XML",
    )
    
    args = parser.parse_args()

    xml_dir = Path(args.folder)
    xml_files = list(xml_dir.glob("*.xml"))
    trackedTeam = str(args.team)
    sm = StatMonkey(xml_files, trackedTeam)

    stats = sm.getAllStats()
    sm.addAllStatsToPres(stats)

if __name__ == "__main__":
    main()