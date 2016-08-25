* Encoding: UTF-8.
* Uses employee data.sav and cars.sav.

compute negsalary = -salary/10.
stats correlations variables=educ to salary.

stats correlations variables=educ to salary negsalary.
sort cases by minority.
split files by minority.
stats correlations variables=salary to jobtime
/with variables = prevexp educ.

sort cases by minority.
split files by minority.
stats correlations variables=educ to salary.

SORT CASES  BY gender minority.
SPLIT FILE LAYERED BY gender minority.
stats correlations variables=educ jobtime salary prevexp.



DATASET ACTIVATE dataset1.
dataset declare @corrs.
CORRELATIONS
  /VARIABLES=educ salbegin minority
/matrix=out(@corrs).

STATS CORRELATIONS VARIABLES=educ jobtime salbegin
/WITH VARIABLES=salary
/OPTIONS CONFLEVEL=95
/MISSING LISTWISE INCLUDE.
split files off.

STATS CORRELATIONS VARIABLES=educ jobtime salbegin
/WITH VARIABLES=salary
/OPTIONS CONFLEVEL=95
/MISSING EXCLUDE=YES PAIRWISE=YES.


STATS CORRELATIONS VARIABLES=educ jobtime salary salbegin
/OPTIONS CONFLEVEL=95
/MISSING EXCLUDE=YES listwise=YES.

DATASET ACTIVATE DataSet1.
STATS CORRELATIONS VARIABLES=accel cylinder engine filter_$ horse mpg weight year
/OPTIONS CONFLEVEL=95
/MISSING INCLUDE=YES.

stats correlations variables =educ
/with variables=salary.

* errors.
stats correlations variables=educ gender.

stats correlations variables=educ salary salbegin/options conflevel=200.

