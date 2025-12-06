import pandas as pd
import io
import re
from collections import defaultdict
import math

# Data preprocessing
def parse_preferences(ranking):
    ranking = ranking.strip()
    print(ranking)
    if ranking.startswith("{") or ranking.endswith("}"):
        return [int(x) for x in ranking[1:-1].split(",")]
    else:
        return int(ranking)

# A function checking if all votes are equal and we have a tie (allowed)
def check_tie(votes_dict):
    values = list(votes_dict.values())
    return all(v == values[0] for v in values)

    
# Alternatives to a dictionary
alternatives = {}
# Rows corresponding to each voter preference
rows = []

# Get all alternatives as a dictionary with number (key) and name
with open("election.txt", "r", encoding="utf8") as f:
    for line in f:
        m = re.match(r"# ALTERNATIVE NAME (\d+):\s*(.*)", line)
        if m:
            i = int(m.group(1))
            name = m.group(2).strip()
            alternatives[i] = name

# Get all voter row preferences as a list
with open("election.txt", "r", encoding="utf8") as f:
    for line in f:
        line = line.strip()
        # removes description rows and empty rows 
        if not line or line.startswith("#"):
            continue
        
        # match voter preference rows
        m = re.match(r"(\d+)\s*:\s*(.*)", line)
        if not m:
            continue

        # Turn rows of the kind: "30: 1,2" into 30 rows of the kind "[1,2]"
        r = line.split(": ")
        for i in range(int(r[0])):
          r1 = r[1].split(",")
          votes = []
          v = []
          while r1:
            # Rows of the kind "1: 1,2,3,{4,5}" are assumed to place {4,5} both as 4th preference
            # They are turned into "[1,2,3,[4,5]]"
            if r1[0].startswith("{"):
              while not r1[0].endswith("}"):
                v.append(int(r1[0][1:]))
                r1.pop(0)
            else:
              if r1[0].endswith("}"):
                v.append(int(r1[0][:-1]))
                r1.pop(0)
                votes.append(v)
                v = []
              else:
                votes.append(int(r1[0]))
                r1.pop(0)
          rows.append(votes)

# Active alternatives are the ones still in the set
active_alternatives = {i: 0 for i in range(1, 12)}
alternatives_k = active_alternatives

# STV rule implementation
while len(active_alternatives) > 1:
    # reset vote counts
    for k in active_alternatives:
        active_alternatives[k] = 0

    # count first-choice votes
    for r in rows:
        # check if r is empty 
        if not r:
            continue

        first = r[0]
        # check if r[0] is an int (3) 
        if isinstance(first, int):
            if first in active_alternatives:
                active_alternatives[first] += 1

        else: # or a list ([1,10])
            active_in_group = [i for i in first if i in active_alternatives]
            if active_in_group:
                weight = 1 / len(active_in_group)
                for i in active_in_group:
                    active_alternatives[i] += weight

    print("Active alternatives:", active_alternatives)
    # check for a tie
    if check_tie(active_alternatives):
        break
    # eliminate the alternative with the lowest votes
    eliminated = min(active_alternatives, key=active_alternatives.get)
    print("Eliminating:", eliminated)
    active_alternatives.pop(eliminated)

    # remove the eliminated alternative from rows which (currently) have it as a first preference
    for r in rows:
        while r:
            first = r[0]

            if isinstance(first, int):
                if first not in active_alternatives:
                    r.pop(0)
                else:
                    break

            else:
                # remove eliminated candidates from list
                first[:] = [i for i in first if i in active_alternatives]

                if not first:  # list is empty
                    r.pop(0)
                else:
                    break

# Get winner(s)
winners = []
i = 0
# Iterate to get winner names 
for alternative in active_alternatives.keys():
    winners.append(f"Alternative {alternative}: {alternatives[alternative]}")
    i+=1
print(f"Winner(s): {winners}")