from MongoDB import Mongo
from lxml import etree
import re
import argparse
from pathlib import Path

# Pull weekly data and parse weekly packages
# Should be able to pull stats with CLA
# Heavy usage of command line parsing
#          kicks[{type, x_start, y_start, x_end, y_end, kicker}]
#           linebreaks[{location{x,y}, player, phase}]
#           mauls[location{x,y}, meters_gained, try_scored?]

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

    def __init__(self, x_start, y_start, x_end, y_end, kick_style, kicker, period):
        self._validate_and_set("x_start", x_start, self._validate_x_coordinate)
        self._validate_and_set("y_start", y_start, self._validate_y_coordinate)
        self._validate_and_set("x_end", x_end, self._validate_x_coordinate)
        self._validate_and_set("y_end", y_end, self._validate_y_coordinate)
        self._validate_and_set("kick_style", kick_style, self._validate_kick_style)
        self._validate_and_set("kicker", kicker, self._validate_string)
        self._validate_and_set("period", period, self._validate_string)

    def _validate_kick_style(self, value, field_name):
        if not isinstance(value, str) or not value.strip():
            self._raise_validation_error(
                "kick_style", "must be a non-empty string", value
            )

        cleaned_value = value.strip().lower()
        if cleaned_value not in self.VALID_KICK_STYLES:
            valid_styles = ", ".join(sorted(self.VALID_KICK_STYLES))
            self._raise_validation_error(
                "kick_style", f"must be one of: {valid_styles}", value
            )
        return cleaned_value


class Break(BaseEvent):
    def __init__(self, x, y, phase, period, player):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("phase", phase, self._validate_string)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)


class Maul(BaseEvent):
    def __init__(self, x, y, meters_gained, period, try_scored):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("meters_gained", meters_gained, self._validate_number)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("try_scored", try_scored, self._validate_boolean)


class TwentyTwoEntry(BaseEvent):
    def __init__(self, points_scored, period, conversion_attempted):
        self._validate_and_set("points_scored", points_scored, self._validate_number)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set(
            "conversion_attempted", conversion_attempted, self._validate_boolean
        )


class PenaltyKick(BaseEvent):
    def __init__(self, x, y, period, phase, distance, player, successful):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("distance", distance, self._validate_number)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("successful", successful, self._validate_boolean)


class GoalKick(BaseEvent):
    def __init__(self, x, y, period, distance, player, successful):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("distance", distance, self._validate_number)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("successful", successful, self._validate_boolean)


class Try(BaseEvent):
    def __init__(self, x, y, player, phase, period):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("period", period, self._validate_string)


class Scrum(BaseEvent):
    def __init__(self, x, y, result, option, period):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("result", result, self._validate_string)
        self._validate_and_set("option", option, self._validate_string)


class PenaltyConceded(BaseEvent):
    def __init__(self, x, y, offense, player, phase, period):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("offense", offense, self._validate_string)


class Turnover(BaseEvent):
    def __init__(self, x, y, player, phase, period, descriptor):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("descriptor", descriptor, self._validate_string)


class PenaltyWon(BaseEvent):
    def __init__(self, x, y, player, phase, period, offense):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("offense", offense, self._validate_string)


class Carry(BaseEvent):
    def __init__(self, x, y, player, phase, period, outcome):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("outcome", outcome, self._validate_string)


class Tackle(BaseEvent):
    def __init__(self, x, y, player, phase, period, contact):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("contact", contact, self._validate_string)


class AtackingLineout(BaseEvent):
    def __init__(self, x, y, period, throw_length, outcome, option):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("throw_length", throw_length, self._validate_string)
        self._validate_and_set("outcome", outcome, self._validate_string)
        self._validate_and_set("option", option, self._validate_string)


class BreakAssists(BaseEvent):
    def __init__(self, x, y, player, phase, period, type):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("type", type, self._validate_string)


class TryAssists(BaseEvent):
    def __init__(self, x, y, player, phase, period, type):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("player", player, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("type", type, self._validate_string)


class Ruck(BaseEvent):
    def __init__(self, x, y, phase, period, speed, outcome):
        self._validate_and_set("x", x, self._validate_x_coordinate)
        self._validate_and_set("y", y, self._validate_y_coordinate)
        self._validate_and_set("period", period, self._validate_string)
        self._validate_and_set("phase", phase, self._validate_number)
        self._validate_and_set("speed", speed, self._validate_string)
        self._validate_and_set("outcome", outcome, self._validate_string)


class StatExtractor:
    FIELD_LENGTH = 140
    FIELD_WIDTH = 68
    TRY_ZONE = 20
    HALFWAY_LINE = FIELD_LENGTH / 2

    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.tree = etree.parse(str(xml_file))
        self.root = self.tree.getroot()
        self.teams = self.get_team_names()
        self.date = self.root.xpath("//SESSION_INFO")[0].text.split()[0]
        print(self.teams)
        self.data = {
            self.teams[0]: {
                "opposition": self.teams[1],
                "kicks": [],
                "linebreaks": [],
                "mauls": [],
                "tries": [],
                "penalties": [],
                "scrums": [],
                "turnovers": [],
                "carries": [],
                "tackles": [],
            },
            self.teams[1]: {
                "opposition": self.teams[0],
                "kicks": [],
                "linebreaks": [],
                "mauls": [],
                "tries": [],
                "penalties": [],
                "scrums": [],
                "turnovers": [],
                "carries": [],
                "tackles": [],
            },
        }

    def get_all(self):
        return self.get_kicks(), self.get_linebreaks(), self.get_mauls()
        # return self.get_kicks(), self.get_linebreaks(), self.get_mauls(), self.get_22_entries(), self.get_penalty_kicks(),
        # self.get_goal_kicks(), self.get_tries(), self.get_scrums(), self.get_pens_conceded(), self.get_turnovers(), self.get_pens_won(),
        # self.get_carries(), self.get_tackles(), self.get_attacking_lineouts(), self.get_defensive_lineouts(), self.get_break_assists(), self.get_try_assists()

    def get_kicks(self):
        home_kicks = self.root.xpath(f"//instance[code='{self.teams[0]} Kick']")
        away_kicks = self.root.xpath(f"//instance[code='{self.teams[1]} Kick']")
        for instance in home_kicks:
            kick = Kick(
                x_start=float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.TRY_ZONE,
                y_start=self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_Start']/text/text()")[0]),
                x_end=float(instance.xpath("label[group='X_End']/text/text()")[0])
                + self.TRY_ZONE,
                y_end=self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_End']/text/text()")[0]),
                kick_style=kick_stlyle,
                kicker=str(
                    instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
                ),
                period=str(
                    instance.xpath("label[group='Period'][position()=1]/text/text()")[0]
                ),
            )
            self.data[self.teams[0]]["kicks"].append(kick.to_dict())

        for instance in away_kicks:
            descriptor = str(
                kick.xpath("label[group='Kick Descriptor']/text/text()")[0]
            )
            style = str(kick.xpath("label[group='Kick Style']/text/text()")[0])
            if descriptor == "Touch Kick":
                continue

            if style == "Box":
                kick_stlyle = "box"
            else:
                kick_stlyle = descriptor

            kick = Kick(
                x_start=float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.TRY_ZONE,
                y_start=self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_Start']/text/text()")[0]),
                x_end=float(instance.xpath("label[group='X_End']/text/text()")[0])
                + self.TRY_ZONE,
                y_end=self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_End']/text/text()")[0]),
                kick_style=kick_stlyle,
                kicker=str(
                    instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
                ),
                period=str(
                    instance.xpath("label[group='Period'][position()=1]/text/text()")[0]
                ),
            )
        return self.data[self.teams[0]]["kicks"].append(kick.to_dict()), self.data[
            self.teams[1]
        ]["kicks"].append(kick.to_dict())

    def get_linebreaks(self):
        home_linebreaks = self.root.xpath(
            f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teams[0]}' and group='Attacking Quality']]"
        )
        away_linebreaks = self.root.xpath(
            f"//instance[label[text='Initial Break' and group='Attacking Qualities'] and label[text='{self.teams[1]}' and group='Attacking Quality']]"
        )
        for instance in home_linebreaks:
            linebreak = Break(
                (
                    float(instance.xpath("label[group='X_Start']/text/text()")[0])
                    + self.TRY_ZONE
                ),
                self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_Start']/text/text()")[0]),
                instance.xpath("label[group='Phase Number'][position()=1]/text/text()")[
                    0
                ],
                instance.xpath("label[group='Period'][position()=1]/text/text()")[0],
                str(
                    instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
                ),
            )
            self.data[self.teams[0]]["linebreaks"].append(linebreak.to_dict())

        for instance in away_linebreaks:
            linebreak = Break(
                (
                    float(instance.xpath("label[group='X_Start']/text/text()")[0])
                    + self.TRY_ZONE
                ),
                self.FIELD_WIDTH
                - float(instance.xpath("label[group='Y_Start']/text/text()")[0]),
                instance.xpath("label[group='Phase Number'][position()=1]/text/text()")[
                    0
                ],
                instance.xpath("label[group='Period'][position()=1]/text/text()")[0],
                str(
                    instance.xpath("label[group='Player'][position()=1]/text/text()")[0]
                ),
            )
            self.data[self.teams[1]]["linebreaks"].append(linebreak.to_dict())

        return self.data[self.teams[0]]["linebreaks"].append(
            linebreak.to_dict()
        ), self.data[self.teams[1]]["linebreaks"].append(linebreak.to_dict())

    def get_mauls(self):
        home_mauls = self.root.xpath(f"//instance[code='{self.teams[0]} Maul']")
        away_mauls = self.root.xpath(f"//instance[code='{self.teams[1]} Maul']")
        for instance in home_mauls:
            maul = {}
            maul["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.TRY_ZONE
            )
            maul["y"] = self.FIELD_WIDTH - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            maul_outcome = str(
                instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0]
            )
            maul["try_scored"] = maul_outcome == "Try Scored"
            maul["meters_gained"] = int(
                instance.xpath("label[group='Maul Metres']/text/text()")[0]
            )
            self.mauls[0].append(maul)

        for instance in away_mauls:
            maul = {}
            maul["x"] = (
                float(instance.xpath("label[group='X_Start']/text/text()")[0])
                + self.TRY_ZONE
            )
            maul["y"] = self.FIELD_WIDTH - float(
                instance.xpath("label[group='Y_Start']/text/text()")[0]
            )
            maul_outcome = str(
                instance.xpath("label[group='Maul Breakdown Outcome']/text/text()")[0]
            )
            maul["try_scored"] = maul_outcome == "Try Scored"
            maul["meters_gained"] = int(
                instance.xpath("label[group='Maul Metres']/text/text()")[0]
            )
            self.mauls[1].append(maul)

        return self.mauls

    def get_22_entries(self):
        home, away = self.get_instances("22 Entry")
        for instance in home:
            pass
        for instance in away:
            pass

    # Get all restart kicks and receptions loop through until you pull both team names
    def get_team_names(self):
        restart_kicks = self.root.xpath("//instance[contains(code, 'Restart Kick')]")
        restart_receptions = self.root.xpath(
            "//instance[contains(code, 'Restart Reception')]"
        )
        teams = []

        for i in range(max(len(restart_kicks), len(restart_receptions))):
            if len(teams) >= 2:
                break
            kick_team = str(restart_kicks[i].xpath("code/text()")[0]).split(" ")[:-2]
            kick_team = " ".join(kick_team)
            receive_team = str(restart_receptions[i].xpath("code/text()")[0]).split(
                " "
            )[:-2]
            receive_team = " ".join(receive_team)
            if kick_team not in teams:
                teams.append(kick_team)
            if receive_team not in teams:
                teams.append(receive_team)

        return teams

    def get_instances(self, code):
        home_instances = self.root.xpath(f"//instance[code='{self.teams[0]} {code}']")
        away_instances = self.root.xpath(f"//instance[code='{self.teams[1]} {code}']")
        return home_instances, away_instances


def main():
    parser = argparse.ArgumentParser(
        description="Process Weekly XML files in a directory"
    )
    parser.add_argument("folder", help="Path to folder containing XML files")

    args = parser.parse_args()
    directory = Path(args.folder)
    files = list(directory.glob("*.xml"))

    db = Mongo()

    for file in files:
        extractor = StatExtractor(str(file))
        teams = extractor.teams
        kicks = extractor.get_kicks()
        linebreaks = extractor.get_linebreaks()
        mauls = extractor.get_mauls()
        for i in range(len(teams)):
            doc = {"date": extractor.date}
            doc["kicks"] = kicks[i]
            doc["linebreaks"] = linebreaks[i]
            doc["mauls"] = mauls[i]
            db.addGame(teams[i], doc)


if __name__ == "__main__":
    main()
