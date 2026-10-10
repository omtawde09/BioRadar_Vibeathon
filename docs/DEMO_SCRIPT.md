# Demo script: five minutes, real data only

Everything below runs on `main` with no internet, apart from the map background tiles (OpenStreetMap). If the venue has no
internet the map shows markers on a grey ground; every other screen is unaffected.

Start the app first: `python -m bioradar.webapp --port 8099`, then open **http://localhost:8099/#review**.
All results are pre-run, so each sample opens in under a second. **Check again now** shows a live run with a timer.

## The one sentence to say first

> "Before today our slides showed a result on a simulated community. Today the same platform checked 50 real public
> sequencing libraries, told us when to collect a new sample, which DNA it cannot name, which fish do not belong in the water,
> and where it was wrong."

Edit the first half to match the slide you actually showed. Do not say anything the slides did not show.

## Minute by minute

| Time | Click | Say (plain words) | What the judge should see |
|---|---|---|---|
| 0:00 | **Numbers & words** tab, scroll to "Real data sets used" | "These are the real public data sets, with links to the archive. Nothing was made up, trimmed or edited. Every file is checked against the archive's own fingerprint." | 5 data sets, links, the reference list version |
| 0:40 | Back to **Sample** tab. The page opens on `G1 - mock MC3 (COI) - authors' own reference` | "This is a mixture of 7 fish whose eggs were counted by hand. The scientists published how much of each fish went in. Our checker found all 7 and the shares are within 3 times of the real ones." | "Check against the recipe" table, `PASS`, "Shares within 3 times: 5 of 5", and the two extra fish it also names, which the paper lists too |
| 1:30 | Picker: `G1 - mock MC3 (COI) - public RefSeq list` | "Now the same DNA judged against the public list, which has no entry for 2 of these fish. The checker did not give them a wrong name. They stay unknown, and the authors' own library tells us what they really are." | "What the unknown DNA really is" table (Oxyjulis californica, Paralichthys californicus). Point at the amber note: some other fish were named that were not in the mixture. Say so out loud. |
| 2:15 | Picker: `GSS356 - British Columbia` | "Only 361 pieces of DNA, and a lot of it is human. The checker says: collect a new sample, and gives a reason for every piece it set aside." | Verdict **Collect a new sample**, reasons on screen |
| 2:45 | Picker: `Irigation point 3 - South Kalimantan` | "Real river water. Nile tilapia and African catfish were found. The alert gives the place, the fish and how serious it is." | Red/amber banner, map pin, action line |
| 3:15 | **Record check** tab | "5,119 real archive records. Future dates, repeated IDs, places outside the protected area and two spellings of one fish were merged or turned away, each with a written reason." | Counts per rule, "database is clean" |
| 3:45 | **Seasons & map** tab, drag the slider | "The same place in August and November: which fish are new, which were not found." Then click **Print a one-page report for this place** | Slider, counts, one-page PDF |
| 4:30 | Back to **Sample**, under "Try your own file" choose a file, press **Check my file** | "A judge can bring any new file. It is checked the same way, shown on screen and deleted. It is not saved." | Full result for the unseen file |
| 4:50 | Language switch (हिन्दी) | "Everything is also in Hindi." | The same page in Hindi |

## What to say about the limits (say it before they ask)

1. "Shares are within 3 times of the real share for about 60% of the fish we could measure. A fish's DNA does not copy at the same rate as another's, so this is expected. We did not tune anything to improve that number."
2. "Three of the 12 mixtures failed our own check: some of their fish were not found. They are in the picker, with the same page."
3. "Some fish that were not in the mixture were still named. A close relative can look almost the same in this gene region."
4. "We show summer against winter, not monsoon against summer: we did not find an Indian pair of seasons in the public archives."
5. "The protected-area line is in Portugal, because that is where real records fall both inside and outside it. It is not an Indian forest."
6. "The match score is a rule of thumb, not a true chance. The screen says so."

## If something goes wrong

| Problem | Do this |
|---|---|
| The page says "Results are not ready yet" | `python -m bioradar.adjudicate.runner all` (about 13 minutes the first time, seconds after) |
| A live re-run feels slow | Say it is a real 15 to 150 second computation in pure Python, then switch to the pre-run result |
| The map has no background | No internet. The markers and the numbers are still correct |
| A file upload is refused | The message says why (empty, not DNA, over 12 MB). Show it. It is the intended behaviour |
