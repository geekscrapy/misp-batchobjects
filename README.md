# misp-batchobjects - Import MISP objects via CSV

Currently, you cannot batch create objects to be added to a MISP Event. This project is aimed at assiting those that need to do this regulary

Objects and their fields are defined within CSV files and provided to the script which creates the associated Object in MISP.

* CSV files MUST contain headers, each of these headers relates to the Objects object-relation field.
* There MUST be an "object" column - this identifies the creating object
* If the object allows it, multiple fields of the same type can be added by appending __1, __2, __3 etc. to the column header. The script strips these suffixes and adds these Attributes individually
* Fields can be in any order
* If the field name is the same across Objects, just use the same column

A file object example:
```
"object","comment","md5","fullpath__1","fullpath__2","filename","filename__2345"
"file,","WanaCry","42af62942e8f576bdd52a46c669de9c1","C:\WINDOWS\tasksche.exe","C:\WINDOWS\qeriuwjhrf","tasksche.exe","qeriuwjhrf"
```
Multiple objects can be included in the same CSV:
```
"object","comment","md5","fullpath__1","fullpath__2","fullpath__3","filename","filename__2","filename__3","ssdeep","ip","domain","url","method","name"
"file","WanaCry","42af62942e8f576bdd52a46c669de9c1","WINDOWS\tasksche.exe","WINDOWS\qeriuwjhrf","WINDOWS\mssecsvr.exe","tasksche.exe","qeriuwjhrf","mssecsvr.exe","24576:QbLguri2QhfdmMSirYbcMNgef0QeQjG/D3k:Qn3QqMSPbcBVQej/",,,,,
"domain-ip","Key request",,,,,,,,,"72.5.65.99","www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwff.com",,,
"http-request",,,,,,,,,,"72.5.65.99",,"http://www.iuqerfsodp9ifjaposdfjhgosurijfaewrwergwff.com/","GET",
```

To show the Objects before uploading to MISP, use --dryrun:

```python batch_objects.py --dryrun -c wanacry_example.csv -i "WanaCry Example"```

# all.csv
This file contains column headers for ALL objects in the 2.4.103 release of MISP
To generate a CSV file of the updated object fields use ```gen_def_csv.sh```

# Custom objects + fields
MISP allows custom objects to be created for an instance - this means that scripts (like this one) usually need a reference to be provided the object json which provides the schema for the object. To do that in this tool use the ```--custom_objects``` flag with the argument set to your custom objects directory. This can be a directory of objects much like https://github.com/MISP/misp-objects/tree/master/objects (this is how the all.csv file is created)

# --help
```
usage: batch_objects.py [-h] (-e (int|uuid) | -i Badstuff ...) [-d [0-4]] -c
                        /path/to/file.csv [/path/to/file.csv ...]
                        [--delim ","] [--quotechar "'"] [--strictcsv]
                        [--custom_objects /path/to/objects/dir/] [--dryrun]
                        [-v]

Upload a CSV of OBJECTS to an EVENT

optional arguments:
  -h, --help            show this help message and exit
  -e (int|uuid), --event (int|uuid)
                        EVENT to add the objects to.
  -i Badstuff ..., --info Badstuff ...
                        Info field if a new event is to be created
  -d [0-4], --distribution [0-4]
                        Distribution level for object attributes - default is
                        Inherit (level 5) - if distribution is set in CSV that
                        overrides this value
  -c /path/to/file.csv [/path/to/file.csv ...], --csv /path/to/file.csv [/path/to/file.csv ...]
                        CSV to create the objects from
  --delim ","           CSV delimiter
  --quotechar "'"       CSV quote character
  --strictcsv           Strict loading of the CSV
  --custom_objects /path/to/objects/dir/
                        If using custom objects provide the path to the
                        objects
  --dryrun              Show objects before sending to MISP
  -v, --verbose         Print debug information to stderr
```
