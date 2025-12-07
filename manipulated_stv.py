import pandas as pd
import io
import re
from collections import defaultdict
import math
import copy
import itertools

def read_election(filename="election.txt"):

    alternatives = {}
    rows = []

    # Get all alternatives as a dictionary with number (key) and name
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            m = re.match(r"# ALTERNATIVE NAME (\d+):\s*(.*)", line)
            if m:
                i = int(m.group(1))
                name = m.group(2).strip()
                alternatives[i] = name

   # Get voter preferences
    with open(filename, "r", encoding="utf8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            m = re.match(r"(\d+)\s*:\s*(.*)", line)
            if not m:
                continue
                    
            number_of_voter = int(m.group(1))
            preference = m.group(2).strip()

            pref_alter = [alter.strip() for alter in preference.split(",")]
            ballot = []
            i = 0
            while i < len(pref_alter):
                p_alter = pref_alter[i]
                # Deal with cases ["1", "2", "3", "{4", "5}"]
                if p_alter.startswith("{"):
                    group = []
                    if p_alter.endswith("}"):
                        inner = p_alter[1:-1].strip()
                        if inner:
                            group.append(int(inner))
                    else:
                        inner = p_alter[1:].strip()
                        if inner:
                            group.append(int(inner))
                        i += 1
                        while i < len(pref_alter):
                            p_alter2 = pref_alter[i].strip()
                            if p_alter2.endswith("}"):
                                inner2 = p_alter2[:-1].strip()
                                if inner2:
                                    group.append(int(inner2))
                                break
                            else:
                                group.append(int(p_alter2))
                            i += 1
                    ballot.append(group)
                else:
                    ballot.append(int(p_alter))
                i += 1

            # Deepcopy every ballot number_of_voter times
            for _ in range(number_of_voter):
                rows.append(copy.deepcopy(ballot))

    return alternatives, rows

# Check if all the alternatives get the same number of votes
def check_tie(votes_dict):

    values = list(votes_dict.values())
    return all(v == values[0] for v in values)

# STV rule implementation
def stv_winner(rows, alternatives):

    rows_local = copy.deepcopy(rows)
    active_alternatives = {i: 0.0 for i in alternatives.keys()}

    while len(active_alternatives) > 1:
        # Reset vote counts
        for k in active_alternatives:
            active_alternatives[k] = 0.0

        # Count first-choice votes
        for r in rows_local:
            if not r:
                continue
            first = r[0]
            if isinstance(first, int):
                if first in active_alternatives:
                    active_alternatives[first] += 1.0
            else:
                active_in_group = [i for i in first if i in active_alternatives]
                if active_in_group:
                    weight = 1.0 / len(active_in_group)
                    for i in active_in_group:
                        active_alternatives[i] += weight

        # Check for a tie
        if check_tie(active_alternatives):
            break

        # Eliminate the alternative with the lowest votes
        min_vote = min(active_alternatives.values())
        lowest = [a for a, v in active_alternatives.items()
                  if abs(v - min_vote) < 1e-9]
        eliminated = min(lowest)
        active_alternatives.pop(eliminated)

        # Remove the eliminated alternative from rows which (currently) have it as a first preference
        for r in rows_local:
            while r:
                first = r[0]

                if isinstance(first, int):
                    if first not in active_alternatives:
                        r.pop(0)
                    else:
                        break

                else:
                    # Remove eliminated candidates from list
                    first[:] = [i for i in first if i in active_alternatives]

                    if not first:  # list is empty
                        r.pop(0)
                    else:
                        break

    return list(active_alternatives.keys())

# Rank the preferences of voters
# The smaller the number, the more voter likes the alternative
def build_rank_of_alternatives(rows, alternatives):

    ranked_alter = []
    # Check every ballot in the rows and start ranking from 1
    for ballot in rows:
        ranked_ballot = {}
        position = 1
        # Get the position in the ranking
        for pref in ballot:
            # Check if the preference in the ballot is [1] or [4,5] 
            if isinstance(pref, int):
                ranked_ballot[pref] = position
                position += 1
            else:
                # If the case is [4,5], which means that 4 and 5 should have the same position
                for same_preference in pref:
                    ranked_ballot[same_preference] = position
                position += 1
        for number in alternatives.keys():
            # Alternatives who have never appeared will be ranked as 999
            if number not in ranked_ballot:
                ranked_ballot[number] = 999
        ranked_alter.append(ranked_ballot)
    return ranked_alter

# Implement the manipulation of a group of voters
def apply_manipulation(rows, manipulated_voters, manipulated_ballot):

    new_rows = copy.deepcopy(rows)
    for voter in manipulated_voters:
        new_rows[voter] = copy.deepcopy(manipulated_ballot)
    return new_rows

# Check the ranking of the manipulated winner to ensure 
# all the manipulated voters like him/her more then the true winner
def manipulated_voters_pref(manipulated_voters, manipulated_winner, true_winner, ranks):

    return all(ranks[voter][manipulated_winner] < ranks[voter][true_winner] for voter in manipulated_voters)


# Make a manipulated ballot to let certain alternative be the manipulated winner
def make_manipulated_ballot(manipulated_winner, true_winner, alternatives):

    '''
    The main idea of the manipulated ballot is to place the manipulated winner at the first place 
    to increase the probability of being winner and move the true winner to the last place to decline 
    the probability of being winner. We implement it because we think it is the easiest and most direct way.

    '''
    all_alters = list(alternatives.keys())
    middle = [a for a in all_alters if a not in (manipulated_winner, true_winner)]
    return [manipulated_winner] + middle + [true_winner]

# Check if the manipulation is successful
def check_manipulation(original_rows, alternatives, ranks,
                       true_winner, manipulated_voters, manipulated_ballot):
   
    new_rows = apply_manipulation(original_rows, manipulated_voters, manipulated_ballot)
    winners = stv_winner(new_rows, alternatives)
    # Check if the winner is only one 
    if len(winners) != 1:
        return winners, False
    new_winner = winners[0]
    prefers = manipulated_voters_pref(manipulated_voters, new_winner, true_winner, ranks)
    return winners, prefers

# Find the smallest group of voters in the manipulation
def find_minimum_manipulated_voters(original_rows, alternatives, ranks,
                            true_winner, max_size=1):
   
    num_voters = len(original_rows)
    all_alts = list(alternatives.keys())

    for manipulated_winner in all_alts:
        if manipulated_winner == true_winner:
            continue

        motivation = [i for i in range(num_voters)
                     if ranks[i][manipulated_winner] < ranks[i][true_winner]]
        if not motivation:
            continue
        
        manipulated_ballot = make_manipulated_ballot(manipulated_winner, true_winner, alternatives)

        for size in range(1, max_size + 1):
            for manipulated_voters in itertools.combinations(motivation, size):
                winners, prefers = check_manipulation(
                    original_rows, alternatives, ranks,
                    true_winner, manipulated_voters, manipulated_ballot
                )
                if len(winners) == 1 and winners[0] == manipulated_winner and prefers:
                    return {
                        "manipulated_winner": manipulated_winner,
                        "manipulated_voters": manipulated_voters,
                        "size": size,
                        "ballot": manipulated_ballot,
                    }
    return None



if __name__ == "__main__":

    alt1, rows1 = read_election("election.txt")

    k = 50
    rows1 = rows1[:k]
    # Get the true winner
    true_winners1 = stv_winner(rows1, alt1)
    print("True winner under STV :", true_winners1)
    true_winner = true_winners1[0]

    # Rank the preference
    ranks1 = build_rank_of_alternatives(rows1, alt1)

    # Mannually change the size
    max_size=10
    result = find_minimum_manipulated_voters(rows1, alt1, ranks1,
                                     true_winner, max_size)

    if result is None:
        print(f"The smallest group is not {max_size} voter")

    else:
        print("\nFind the small group: ")
        print("  Manipulated_winner:", result["manipulated_winner"], f"({alt1[result['manipulated_winner']]})")
        print("  Size:", result["size"])
        print("  Voters:", result["manipulated_voters"])
        print("  Ballot:", result["ballot"])
