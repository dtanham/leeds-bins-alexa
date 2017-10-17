import pymysql, sys

# A nearby property for testing purposes
property_id = "12345"
# Load variables for this environment
from prod_env.py import *

jobs_file = '../data/dm_jobs.datefix.csv'
premises_file = '../data/dm_premises.csv'

conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)

def create_tables():
	with conn.cursor() as cur:
		cur.execute("CREATE TABLE IF NOT EXISTS bin_collections (property_id varchar(255), collection_type varchar(255), collection_date date)")
		conn.commit()

	with conn.cursor() as cur:
		cur.execute("CREATE TABLE IF NOT EXISTS bin_locations (property_id varchar(255), street varchar(255))")
		conn.commit()

def load_tables():
	drop_tables()
	create_tables()
	with conn.cursor() as cur:

		with open(jobs_file) as f:
			data = f.readlines()[1:]
			count = 0
			for collection in data:
				(p_id, collection_type, collection_date) = collection.strip().split(',')
				cur.execute("INSERT INTO bin_collections (property_id, collection_type, collection_date) values(%s, %s, %s)", (p_id, collection_type, collection_date))
				conn.commit()
				count += 1
			print "Loaded "+str(count)+" collection records"

	with conn.cursor() as cur:

		with open(premises_file) as f:
			data = f.readlines()[1:]
			count = 0

			streets = set()

			for premise in data:
				(p_id, a1, a2, street, locality, town) = premise.strip().split(',')
				if street not in streets:
					cur.execute("INSERT INTO bin_locations (property_id, street) values(%s,%s)", (p_id, street))
					conn.commit()
					streets.add(street)
				count += 1
			print "Loaded "+str(count)+" premise records"


def drop_tables():
	with conn.cursor() as cur:
		cur.execute("drop table if exists bin_collections")
		cur.execute("drop table if exists bin_locations")
		conn.commit()


def next_bin():
	with conn.cursor() as cur:
		cur.execute("select * from bin_collections where property_id=%s and collection_date > now() order by collection_date asc limit 1", property_id)
		print cur.fetchone()


