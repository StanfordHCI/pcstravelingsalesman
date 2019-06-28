# PCS Traveling Salesman
This Python program orders the papers in PCS to minimize traffic in and out of the room due to conflicts. It batches papers into groups (e.g., all papers with average score between 3.0 and 3.25), and then orders papers within each group. The idea is that the committee will pick a group, then walk its way through the list following the order specified in this program. You might start with the papers ranked 4.5 or above, then jump down to the 3.0-3.25s, then back up to the 4.25-4.5s, etc. The papers are ordered within each group to minimize the numbers of ins-and-outs. The program does not optimize across groups.

The output is a CSV that specifies the order. The 'order' column indicates the order that you should touch the paper. Unfortunately, as of June 2019, PCS does not have functionality for PC chairs to create a label that can be shared with other program committee members for sorting their view of all submissions. The way to address this is to create a new Decision in PCS for each paper. The 'label' column in the CSV is the decision to create and assign to that paper. The numbers are in the opposite order as the 'order' column because the committee typically sorts their view descending by Decision so that the top-rated papers are at the top. (Though to be fair, a traveling salesman walk is optimal no matter whether you traverse it forwards or backwards, so go nuts.) If ACs want to add other papers to the traversal, create another decision such as (TS_extra) to put them on the queue.

## Assumptions
We assume that PC members have entered conflicts into PCS. In UIST 2019, this happened as a part of the AC paper bidding phase, so we are able to see 'C's for conflicts in the paper bidding CSV. Make sure this applies to you, or you'll need another way to track conflicts.

## Running the program
First, change the parameters in pcs-travelingsalesman.py:
`SCORE_STEPS = [3.01, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75]`
This groups papers into batches of this score range (e.g., .25 = 3.25-3.50) for discussion. This list defines the minimum and maximum score range to be discussed, as well as how large the make the groups. For UIST 2019, discussing all papers of average score > 3.0 in groups of score range .25 worked well.

`OUTPUT_CSV = 'uist19a_travelingsalesman_order.csv'`
Where the output should be written to.

`BIDDING_CSVS = ['uist19a_committee_bidding-msb.csv', 'uist19a_committee_bidding-reinecke.csv', 'uist19a_committee_bidding-andrewhead.csv']`
Bidding CSVs from PCS: this is the only CSV that contains conflict information in PCS, so we use it. This may be a list of CSVs if needed, since one of the ACs may be conflicted with a paper and that one won't show up in their CSV. This just merges all the CSVs in the list.

`SUBMISSION_CSV = 'uist19a_submission.csv'`
Submission CSV: we use this as an index of all the papers and their current overall scores

I am assuming that you are using Python 3. If not:
```
virtualenv -p python3 pcsenv
source pcsenv/bin/activate
```

Then, to run:
```
pip install -r requirements.txt
python3 pcs-travelingsalesman.py
```

## How does it work?
Think of each paper as a node in a graph. We encode the distance between two nodes (papers) as the size of the symmmetric difference between the conflicts for each paper. In other words, it's the number of conflicts that the two papers don't have in common. If Paper 1 has conflicts A and B, and Paper 2 has conflicts B and C, then their distance is 2, since A will have to re-enter the room and C will have to leave the room if we transition from Paper 1 to Paper 2. If Paper 2 instead had conflicts A, B, and C, the distance would be 1 because only A would need to re-enter the room.

We then find a traveling salesman path across all papers in the group that touches each paper once while minimizing the total distance.

## Who do I blame for this?
By Michael Bernstein (Stanford University), June 2019, originally for UIST 2019. Thanks to Adam Finkelstein (Princeton) and David Karger (MIT) for advice.
