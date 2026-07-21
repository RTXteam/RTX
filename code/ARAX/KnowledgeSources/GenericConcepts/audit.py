import csv


def load(path):
    with open(path, newline="") as f:
        return {(r["TestCase"], r["TestAsset"]): r for r in csv.DictReader(f)}


old = load("test_suite_results.csv")       # old blocklist
new = load("test_suite_results_new.csv")   # new blocklist

regressions = []    # previously PASS, now FAIL
progressions = []   # previously FAIL, now PASS

for key in old.keys() & new.keys():
    was = old[key]["Result"]
    now = new[key]["Result"]
    if was == "PASS" and now == "FAIL":
        regressions.append(new[key])
    elif was == "FAIL" and now == "PASS":
        progressions.append(new[key])

fields = ["TestCase", "TestAsset", "name", "url"]


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


write("regression.csv", regressions)
write("progression.csv", progressions)

print(f"regressions  (PASS -> FAIL): {len(regressions):3}  -> regression.csv")
print(f"progressions (FAIL -> PASS): {len(progressions):3}  -> progression.csv")