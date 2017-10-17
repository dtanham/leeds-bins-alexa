count = 0

with open("../data/dm_jobs.csv") as f:
	data = f.readlines()

	with open("../data/dm_jobs.datefix.csv", "w") as w:
		w.write(data[0].strip()+"\n")
		for d in data[1:]:
			parts = d.strip().split(',')
			collection_date = parts[2]
			parts[2] = "20"+collection_date[6:]+"-"+collection_date[3:5]+"-"+collection_date[:2]
			w.write(",".join(parts)+"\n")
			count += 1

print "Reformatted "+str(count)+" dates into something sensible"