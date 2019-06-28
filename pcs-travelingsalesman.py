# Python 3
# Uses PCS exports to produce a traveling salesman solution to ordering the papers for discussion
# Created by Michael Bernstein in June 2019. MIT License.

import csv
from collections import defaultdict
import pprint
from numpy import median
import pandas as pd
import sys
import math
import tsp
import numpy as np

# Group papers into batches of this score range (e.g., .25 = 3.25-3.50) for discussion
# This defines the minimum and maximum score range to be discussed
SCORE_STEPS = [3.01, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75]

# Where the output should be written to.
OUTPUT_CSV = 'uist19a_travelingsalesman_order.csv'
# Bidding CSVs from PCS: this is the only CSV that contains conflict information in PCS, so we use it.
# This may be a list of CSVs if needed, since one of the ACs may be conflicted with a paper
# and that one won't show up in their CSV. This just merges all the CSVs in the list.
BIDDING_CSVS = ['uist19a_committee_bidding-msb.csv', 'uist19a_committee_bidding-reinecke.csv', 'uist19a_committee_bidding-andrewhead.csv']
# Submission CSV: we use this as an index of all the papers and their current overall scores
SUBMISSION_CSV = 'uist19a_submission.csv'

# get the set of papers that will be discussed
def load_eligible_papers(filename, min_score, max_score):
    with open(filename) as reviewfile:
        df = pd.read_csv(reviewfile)
        df['Overall Score'] = pd.to_numeric(df['Overall Score'])
        df = df[pd.notnull(df['Overall Score'])]
        df = df[df['Overall Score'] >= min_score]
        df = df[df['Overall Score'] < max_score]
        df = df.sort_values(by=['Overall Score'], ascending=False)
        papers = df['Paper ID'].tolist()
        print(papers)
        return papers


# load the conflicts from the PCS file
def load_conflicts(file_list, eligible_papers):
    conflicts = dict()
    ac_columns = dict()

    for filename in file_list: #will do some redundant work, but that's ok
        with open(filename) as conflictfile:
            reader = csv.reader(conflictfile)
            row_num = 0
            for row in reader:
                row_num += 1
                if row_num == 1 or row_num == 2 or row_num == 4 or row_num == 5: # blank or not useful  lines
                    continue
                elif row_num == 3:
                    for i in range(2, len(row)): # skip the first couple of columns because they just give the paper number and title
                        ac_columns[i] = row[i].split('\n')[0]
                else:
                    sub_id = row[0]
                    if sub_id in eligible_papers:
                        conflicts[sub_id] = list()
                        for i in range(2, len(row)): # skip the first couple of columns because they just give the paper number and title
                            if (i-2) % 3 == 0: # bid column
                                if row[i] == "C": # conflict
                                    conflicts[sub_id].append(ac_columns[i])
    return ac_columns, conflicts

# load the ACs from a PCS file
def load_ACs(filename, eligible_papers):
    acs = defaultdict(list)
    with open(filename) as reviewfile:
        reader = csv.DictReader(reviewfile)
        for row in reader:
            role = row['Role']
            submission = row['\ufeffSub ID']#row['\xef\xbb\xbfSub ID']
            if submission in eligible_papers:
                if role is not None and 'AC' in role:
                    acs[submission].append(row['Reviewer'])
    return acs

# Return pairs of papers that cannot be in the same group: an AC from one paper is conflicted the other paper
def create_costs(conflicts):
    costs = list()
    for paper1 in conflicts.keys():
        paper1_distances = list()
        for paper2 in conflicts.keys():
            paper1_conflicts = set(conflicts[paper1])
            paper2_conflicts = set(conflicts[paper2])
            difference = paper1_conflicts.symmetric_difference(paper2_conflicts)
            cost = 0
            if len(difference) > 0:
                cost = len(difference)#1

            paper1_distances.append(cost)
        costs.append(paper1_distances)
    return costs

# Create a graph coloring, to identify sets of nodes (papers) that are safe to discuss together
def construct_tsp(costs):
    print("Solving traveling salesman problem. Did you know this is NP-hard? COME ON, GIVE ME A SEC!")
    r = range(len(costs))
    dist = {(i, j): costs[i][j] for i in r for j in r}
    tsp_result = tsp.tsp(r, dist)
    return tsp_result[1]


# Split the papers into groups with additional metadata
def split_into_groups(tsp_result, conflicts):
    groups = list()
    step = 0
    papers_per_group = 1 # increase this if you want to batch papers out and send conflicts out for multiple papers at once (e.g., "next two papers, get out") to reduce cross traffic. We ultimately chose not to do this.
    while step < len(tsp_result):
        indices = tsp_result[step:step+1]
        subgroup = [list(conflicts.keys())[paper] for paper in indices]
        groups.append(create_subgroup(subgroup, conflicts))
        step += len(subgroup)

    return groups


# Returns a structured subgroup for a set of papers
def create_subgroup(subgroup, conflicts):
    group_conflicts = set()
    for subgroup_paper in subgroup:
        group_conflicts.update(conflicts[subgroup_paper])
    return {
        'papers': subgroup,
        'conflicts': group_conflicts
    }

def print_moves(title, groups, ac_columns):
    num_papers = 0
    is_in_room = defaultdict(lambda: True)
    total_movements = 0
    at_least_one_movements = 0
    for i, group in enumerate(groups):
        num_papers += len(group['papers'])

        # calculate symmetric difference
        paper1_conflicts = group['conflicts']
        if i > 0:
            paper2_conflicts = groups[i-1]['conflicts']
        else:
            paper2_conflicts = set()
        difference = paper1_conflicts.symmetric_difference(paper2_conflicts)

        print("%s: %d movements, now out of room: %s" % (group['papers'], len(difference), group['conflicts']))
        has_at_least_one_move = False
        for ac in set(ac_columns.values()):
            is_conflicted = ac in group['conflicts']

            if is_in_room[ac] and is_conflicted:
                total_movements += 1
                is_in_room[ac] = False
                has_at_least_one_move = True
            elif not is_in_room[ac] and not is_conflicted:
                total_movements += 1
                is_in_room[ac] = True
                has_at_least_one_move = True
        if has_at_least_one_move:
            at_least_one_movements += 1
    print("%s: total person movements in and out of the room: %d" % (title, total_movements))
    print("%s: total papers requiring at least one move in or out: %d" % (title, at_least_one_movements))
    print("%s: %d total papers" % (title, num_papers))

# how much time do ACs spend out of the room?
def print_AC_stats(ac_columns, all_conflicts, groups, all_eligible_papers):

    print_moves("If we go by score descending order", [create_subgroup([paper], all_conflicts) for paper in all_eligible_papers], ac_columns)
    print("\n\n\n-----\n\n\n")
    print_moves("If we go by TSP order", groups, ac_columns)

# output the CSV with the papers, the order to run them in, and the decision label to give them
def append_CSV(writer, groups, cur_min_score):
    for i, group in enumerate(groups):
        for paper in group['papers']:
            # in order for the descending sort to work in PCS, we need to actually apply a label that is the reverse of the intended traversal order. In other words, TS3.00-1 will be the last one in the sort, and TS3.00-9 (assuming nine entries) will be the first one. So, we reverse the order of the labels, which keeps us with the original order. Technically this isn't necessary because the traveling salesman solution is reversible, but this way the output from the program in the terminal matches the traversal order in PCS.
            d = {
                'paper': paper,
                'group': cur_min_score,
                'order': i+1,
                'label': 'TS%.2f-%d' % (cur_min_score, len(groups) - i),
                'conflicts': group['conflicts'] if len(group['conflicts']) > 0 else '{}'
            }
            writer.writerow(d)

if __name__ == "__main__":
    all_groups = list()
    all_conflicts = dict()
    all_ac_columns = dict()
    all_eligible_papers = set()

    with open(OUTPUT_CSV, 'w') as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=['paper', 'group', 'order', 'label', 'conflicts'])
        writer.writeheader()

        # We will iterate by score range (e.g., 3.5-3.25, then 3.25-3.0, then...)
        for index in range(len(SCORE_STEPS)-1):
            cur_min_score = SCORE_STEPS[index]
            cur_max_score = SCORE_STEPS[index+1]
            # Submissions CSV from PCS
            eligible_papers = load_eligible_papers(SUBMISSION_CSV, cur_min_score, cur_max_score)
            print("Range [%.2f, %.2f): %d papers" % (cur_min_score, cur_max_score, len(eligible_papers)))
            all_eligible_papers.update(eligible_papers)

            ac_columns, conflicts = load_conflicts(BIDDING_CSVS, eligible_papers)
            print("Conflicts loaded for %d ACs on %d papers." % (len(ac_columns.keys()), len(conflicts.keys())))
            all_conflicts.update(conflicts)

            # Now, create the distances of traversing from each paper to each other paper
            costs = create_costs(conflicts)
            print("Cost structure:")
            print(costs)

            # Solve the traveling salesman problem
            tsp_result = construct_tsp(costs)
            print('Recommended path: %s' % tsp_result)

            # Slim the coloring down into groups of reasonable size
            #inverted_coloring = descriptive_stats(coloring, conflicts)
            groups = split_into_groups(tsp_result, conflicts)
            all_groups.extend(groups)
            all_ac_columns = ac_columns

            append_CSV(writer, groups, cur_min_score)

    # Print some checking information about how much the ACs are out of the room
    print_AC_stats(all_ac_columns, all_conflicts, all_groups, all_eligible_papers)
