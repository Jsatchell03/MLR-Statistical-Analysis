import argparse
from lxml import etree
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Process XML files in a directory")
    parser.add_argument("file", help="Path to XML file")
    parser.add_argument(
        "team",
        help="Team name spelt and capitalize the exact way it is referenced in Oval Insights XML",
    )

    args = parser.parse_args()

    xml_file = Path(args.file)
    team = str(args.team)

    stats1 = sm.getAllStats()
    sm.addAllStatsToPres(stats1)


if __name__ == "__main__":
    main()
