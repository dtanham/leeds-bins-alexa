# Leeds Bin Collections

At this stage it works for me, which is good enough for a few beers on a Monday.

## Deployment notes

Use convert_dates.py to convert the DataMill North CSV into a MySQL-compatible date format, then load into a MySQL-compatible database with a similar schema (```varchar, varchar, date```).

For Leeds, grab [this](https://datamillnorth.org/dataset/household-waste-collections) from the DataMill North DataPress site.

Create a prod_env.py file with the following populated variables:

* rds_host
* name
* password
* db_name
* skill_id

Zip up this directory with: ```zip -r deploy.zip *``` and upload to lambda. (This is why all the python dependencies are given here - needs cleaning)