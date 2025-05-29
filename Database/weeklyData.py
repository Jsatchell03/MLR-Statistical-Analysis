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


class ValidationError(ValueError):
    """Custom exception for validation errors with class and field context"""

    def __init__(self, class_name, field_name, message, value):
        self.class_name = class_name
        self.field_name = field_name
        self.message = message
        self.value = value

        # Format the error message with or without the value
        # Truncate long values for readability
        value_str = str(value)
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        super().__init__(f"{class_name}.{field_name}: {message} (got: {value_str})")


class BaseEvent:
    """Base class for all rugby events with common validation"""

    def _raise_validation_error(self, field_name, message, value):
        """Helper method to raise validation errors with class context"""
        raise ValidationError(self.__class__.__name__, field_name, message, value)

    def _validate_and_set(self, field_name, value, validator_func):
        """Validate a value and set it as an attribute"""
        validated_value = validator_func(value, field_name)
        setattr(self, field_name, validated_value)

    def _validate_x_coordinate(self, value, field_name):
        """Validate x coordinates"""
        if not isinstance(value, (int, float)):
            self._raise_validation_error(field_name, "must be a number", value)
        if value < -10 or value > 150:  # Assuming field dimensions
            self._raise_validation_error(field_name, "must be between 0 and 150", value)
        return value

    def _validate_y_coordinate(self, value, field_name):
        """Validate y coordinates"""
        if not isinstance(value, (int, float)):
            self._raise_validation_error(field_name, "must be a number", value)
        if value < -10 or value > 80:  # Assuming field dimensions
            self._raise_validation_error(
                field_name, "must be between -10 and 80", value
            )
        return value

    def _validate_period(self, period, field_name):
        """Validate period number"""
        if not isinstance(period, int):
            self._raise_validation_error(field_name, "must be an integer", period)
        if period < 1 or period > 2:  # Assuming 2 periods in XML files
            self._raise_validation_error(field_name, "must be 1 or 2", period)
        return period

    def _validate_string(self, value, field_name):
        """Validate string fields"""
        if not isinstance(value, str) or not value.strip():
            self._raise_validation_error(
                field_name, "must be a non-empty string", value
            )
        return value.strip()

    def _validate_number(self, value, field_name):
        """Validate numeric fields (cannot be negative)"""
        if not isinstance(value, (int, float)):
            self._raise_validation_error(field_name, "must be a number", value)
        if value < 0:
            self._raise_validation_error(field_name, "must be a positive number", value)
        return value

    def _validate_boolean(self, value, field_name):
        """Validate boolean fields"""
        if not isinstance(value, bool):
            self._raise_validation_error(field_name, "must be True or False", value)
        return value

    def to_dict(self):
        """Convert to dictionary for MongoDB"""
        return self.__dict__


# Base Event and Custom Error done finish rest
class Kick(BaseEvent):
    VALID_KICK_STYLES = {"box", "territorial", "low", "bomb", "chip", "cross pitch"}

    def __init__(self, xStart, yStart, xEnd, yEnd, kickStyle, kicker, period):
        self.xStart = xStart
        self.yStart = yStart
        self.xEnd = xEnd
        self.yEnd = yEnd
        self.kickStyle = kickStyle
        self.kicker = kicker
        self.period = period

    def _validate_kick_styles(self, value):
        if not isinstance(value, str) or not value.strip():
            self._raise_validation_error(
                "Kick Style", "must be a non-empty string", value
            )

        cleaned_value = value.strip().lower()
        if cleaned_value not in self.VALID_KICK_STYLES:
            valid_styles = ", ".join(sorted(self.VALID_KICK_STYLES))
            self._raise_validation_error(
                "Kick Style", f"must be one of: {valid_styles}", value
            )
        return cleaned_value


class Breaks(BaseEvent):
    def __init__(self, x, y, phase, period, player):
        self.x = x
        self.y = y
        self.phase = phase
        self.period = period
        self.player = player


class Mauls(BaseEvent):
    def __init__(self, x, y, metersGained, period, tryScored):
        self.x = x
        self.y = y
        self.metersGained = metersGained
        self.period = period
        self.tryScored = tryScored


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
        # return self.getKicks(), self.getLinebreaks(), self.getMauls(), self.get22Entries(), self.getPenaltyKicks(),
        # self.getGoalKicks(), self.getTries(), self.getScrums(), self.getPensConceded(), self.getTurnovers(), self.getPensWon(),
        # self.getCarries(), self.getTackles(), self.getAttackingLineouts(), self.getDefensiveLineouts(), self.getBreakAssists(), self.getTryAssists()

    def getKicks(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeKicks = root.xpath(f"//instance[code='{self.teams[0]} Kick']")
        awayKicks = root.xpath(f"//instance[code='{self.teams[1]} Kick']")
        for instance in homeKicks:
            kick = {}
            descriptor = str(
                instance.xpath("label[group='Kick Descriptor']/text/text()")[0]
            )
            if descriptor == "Touch Kick":
                continue
            kick["kicker"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            kick["xStart"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            kick["yStart"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            kick["xEnd"] = (
                float(instance.xpath("label[group='X_End']/text/text()")[0])
                + self.tryZone
            )
            kick["yEnd"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_End']/text/text()")[0]
            )
            kickStyle = str(instance.xpath("label[group='Kick Style']/text/text()")[0])
            if kickStyle == "Box":
                kick["type"] = "windy"
            else:
                match descriptor:
                    # Pocket
                    case "Territorial":
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
            descriptor = str(
                instance.xpath("label[group='Kick Descriptor']/text/text()")[0]
            )
            if descriptor == "Touch Kick":
                continue
            kick["kicker"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            kick["xStart"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            kick["yStart"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            kick["xEnd"] = (
                float(instance.xpath("label[group='X_End']/text/text()")[0])
                + self.tryZone
            )
            kick["yEnd"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_End']/text/text()")[0]
            )
            kickStyle = str(instance.xpath("label[group='Kick Style']/text/text()")[0])
            if kickStyle == "Box":
                kick["type"] = "windy"
            else:
                match descriptor:
                    # Pocket
                    case "Territorial":
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
            linebreak["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            linebreak["y"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            linebreak["phase"] = instance.xpath(
                "label[group='Phase Number'][position()=1]/text/text()"
            )[0]
            linebreak["player"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            self.linebreaks[0].append(linebreak)

        for instance in awayLinebreaks:
            linebreak = {}
            linebreak["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            linebreak["y"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            linebreak["phase"] = instance.xpath(
                "label[group='Phase Number'][position()=1]/text/text()"
            )[0]
            linebreak["player"] = str(
                instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
            )
            self.linebreaks[1].append(linebreak)

        return self.linebreaks

    def getMauls(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeMauls = root.xpath(f"//instance[code='{self.teams[0]} Maul']")
        awayMauls = root.xpath(f"//instance[code='{self.teams[1]} Maul']")
        for instance in homeMauls:
            maul = {}
            maul["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            maul["y"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            maulOutcome = str(
                instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0]
            )
            maul["tryScored"] = maulOutcome == "Try Scored"
            maul["metersGained"] = int(
                instance.xpath("label[group='Maul Metres']/text/text()")[0]
            )
            self.mauls[0].append(maul)

        for instance in awayMauls:
            maul = {}
            maul["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.tryZone
            )
            maul["y"] = self.fieldWidth - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            maulOutcome = str(
                instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0]
            )
            maul["tryScored"] = maulOutcome == "Try Scored"
            maul["metersGained"] = int(
                instance.xpath("label[group='Maul Metres']/text/text()")[0]
            )
            self.mauls[1].append(maul)

        return self.mauls

    def get22Entries(self):
        home, away = self.getInstances("22 Entry")
        for instance in home:
            pass
        for instance in away:
            pass

    # Get all restart kicks and recpetions loop through until you pull both team names
    def getTeamNames(self):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()

        restartKicks = root.xpath("//instance[contains(code, 'Restart Kick')]")
        restartReceptions = root.xpath(
            "//instance[contains(code, 'Restart Reception')]"
        )
        teams = []

        for i in range(max(len(restartKicks), len(restartReceptions))):
            if len(teams) >= 2:
                break
            kickTeam = str(restartKicks[i].xpath("code/text()")[0]).split(" ")[:-2]
            kickTeam = " ".join(kickTeam)
            receiveTeam = str(restartReceptions[i].xpath("code/text()")[0]).split(" ")[
                :-2
            ]
            receiveTeam = " ".join(receiveTeam)
            if kickTeam not in teams:
                teams.append(kickTeam)
            if receiveTeam not in teams:
                teams.append(receiveTeam)

        return teams

    def getInstances(self, code):
        tree = etree.parse(str(self.xmlFile))
        root = tree.getroot()
        homeInstances = root.xpath(f"//instance[code='{self.teams[0]} {code}']")
        awayInstances = root.xpath(f"//instance[code='{self.teams[1]} {code}']")
        return homeInstances, awayInstances


def main():
    parser = argparse.ArgumentParser(
        description="Process Weekly XML files in a directory"
    )
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


if __name__ == "__main__":
    main()
